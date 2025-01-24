from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
from sentence_transformers import SentenceTransformer
import pandas as pd
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
import json
from io import StringIO
import uvicorn

# FastAPI setup
app = FastAPI()

# 1. Connect to Milvus
connections.connect("default", host="localhost", port="19530")

# 2. Define Collection Schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384),
    FieldSchema(name="metadata", dtype=DataType.JSON)  # Store Name, Address, etc.
]
schema = CollectionSchema(fields, description="Distributed vector database with metadata")
collection_name = "distributed_vector_db"

# 3. Create or Load Collection
try:
    collection = Collection(name=collection_name)
except:
    collection = Collection(name=collection_name, schema=schema, shards_num=4)  # Set sharding here

# 4. Initialize Sentence Transformer Model
model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

# 5. API Models
class VectorInsert(BaseModel):
    Name: str
    Address: str
    Email: str
    PhoneNumber: str

class VectorQuery(BaseModel):
    query_text: str
    top_k: int

# 6. Helper Functions
def embed_text(text: str):
    """Generate a vector embedding for a given text."""
    return model.encode(text).tolist()

def batch_insert(data: pd.DataFrame, collection: Collection):
    """Insert a batch of data into Milvus."""
    vectors = [embed_text(name) for name in data["Name"]]
    metadata = data.drop(columns=["vector"]).to_dict(orient="records")
    collection.insert([vectors, metadata])
    return len(vectors)

# Function to process the NDJSON file and map data to fit the schema
def process_ndjson_line(line: str):
    """Convert an NDJSON line to fit the collection schema."""
    data = json.loads(line)
    
    # Map fields from NDJSON to the collection schema
    # Assuming Name is a combination of FIRST_NAME and LAST_NAME
    name = f"{data.get('FIRST_NAME', '')} {data.get('LAST_NAME', '')}"
    
    return {
        "Name": name,
        "Address": data.get('ADDRESS', ''),
        "Email": data.get('EMAIL', ''),
        "PhoneNumber": data.get('PHONE', '')
    }

# 7. Routes
@app.post("/insert", summary="Insert a new vector and metadata")
async def insert_vector(vector_data: VectorInsert):
    """Insert a single vector."""
    vector = embed_text(vector_data.Name)
    metadata = {
        "Name": vector_data.Name,
        "Address": vector_data.Address,
        "Email": vector_data.Email,
        "PhoneNumber": vector_data.PhoneNumber
    }
    collection.insert([[vector], [metadata]])
    return {"message": "Vector inserted successfully."}

@app.post("/query", summary="Query for similar vectors")
async def query_vectors(query: VectorQuery):
    """Query similar vectors based on input text."""
    query_vector = embed_text(query.query_text)
    search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
    results = collection.search(
        data=[query_vector],
        anns_field="vector",
        param=search_params,
        output_fields=["metadata"],
        limit=query.top_k
    )
    response = []
    for result in results[0]:
        response.append({
            "ID": result.id,
            "Score": result.score,
            "Metadata": result.entity.get("metadata")
        })
    return response

@app.get("/stats", summary="Get database statistics")
async def get_stats():
    """Return detailed stats on the database."""
    stats = {
        "collection_name": collection.name,
        "description": collection.description,
        "is_empty": collection.is_empty,
        "total_vectors": collection.num_entities,
        "primary_field": collection.primary_field.name,
        "primary_field_type": str(collection.primary_field.dtype),
        "partitions": [partition.name for partition in collection.partitions],
        "indexes": [
            {
                "field_name": index.field_name,
                "index_type": index.params.get("index_type", "unknown"),
                "metric_type": index.params.get("metric_type", "unknown"),
                "params": index.params,
            }
            for index in collection.indexes
        ],
    }
    return stats

@app.delete("/delete/{vector_id}", summary="Delete a vector by ID")
async def delete_vector(vector_id: int):
    """Delete a vector by its ID."""
    collection.delete(expr=f"id in [{vector_id}]")
    return {"message": f"Vector with ID {vector_id} deleted successfully."}

@app.post("/batch_insert", summary="Batch insert vectors")
async def batch_insert_vectors(data: list[VectorInsert]):
    """Batch insert vectors into the database."""
    df = pd.DataFrame([item.dict() for item in data])
    df["vector"] = df["Name"].apply(embed_text)
    count = batch_insert(df, collection)
    return {"message": f"{count} vectors inserted successfully."}

@app.post("/upload_file/", summary="Upload NDJSON file and insert vectors")
async def upload_file(file: UploadFile = File(...)):
    """API endpoint to upload NDJSON file and insert into Milvus."""
    try:
        # Process the file line by line
        content = await file.read()
        lines = content.decode().splitlines()

        # Prepare the data in batches
        batch_size = 1000  # You can adjust this based on your memory limitations
        batch_data = []
        
        for i, line in enumerate(lines):
            processed_data = process_ndjson_line(line)
            batch_data.append(processed_data)
            
            # If batch size reached, insert into Milvus
            if len(batch_data) >= batch_size:
                df = pd.DataFrame(batch_data)
                batch_insert(df, collection)
                batch_data = []  # Reset batch

        # Insert any remaining data
        if batch_data:
            df = pd.DataFrame(batch_data)
            batch_insert(df, collection)

        return {"message": f"File processed and {len(lines)} lines uploaded successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# 8. Indexing and Loading (for scalability)
collection.create_index(
    field_name="vector",
    index_params={
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 48, "efConstruction": 400}
    }
)
collection.load()  # Corrected load method

# Main entry point
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
