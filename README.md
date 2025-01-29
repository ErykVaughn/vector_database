# EC2 Setup for Milvus and FastAPI

This guide will walk you through the steps of setting up an EC2 instance, installing necessary software, and setting up Milvus (Vector Database) and FastAPI for your project.

## Step 1: Create an EC2 Instance
### 1️⃣ Log into AWS Console
Go to the AWS Management Console → Open EC2 Dashboard.
### 2️⃣ Launch an EC2 Instance
Click "Launch Instance".

#### Choose an AMI:

Select Amazon Linux 2 (recommended) or Ubuntu 22.04.
#####Choose an instance type:

Minimum: t3.large (8GB RAM) ✅ Recommended
If handling large-scale data, consider m5.large or g4dn.xlarge (for GPU acceleration).
#### Key Pair:

Create a new key pair (if you don’t have one) and download it.
This is required for SSH access.
#### Network Settings:

Under Security Group, create new rules:
Port 22 (SSH) → Allow your IP.
Port 8000 (FastAPI) → Allow anywhere (0.0.0.0/0).
Port 19530 (Milvus) → Allow anywhere (0.0.0.0/0).
Port 2379 (ETCD) → Allow anywhere (0.0.0.0/0).
Port 9000 (MinIO) → Allow anywhere (0.0.0.0/0).
#### Storage:

Set at 20GB or more.
Click Launch and wait for the instance to start.

## Step 2: Connect to Your EC2 Instance
### 1️⃣ Find Your EC2 Public IP
In AWS EC2 Dashboard → Find your instance → Copy Public IPv4 address.
### 2️⃣ SSH into the Instance
#### Open a terminal and run:

sh
Copy
Edit
ssh -i /path/to/your-key.pem ec2-user@your-ec2-public-ip
(Replace /path/to/your-key.pem with your downloaded key.)

If using Ubuntu, the username is ubuntu instead of ec2-user:

sh
Copy
Edit
ssh -i /path/to/your-key.pem ubuntu@your-ec2-public-ip
## Step 3: Install Required Software
### 1️⃣ Update the System
sh
Copy
Edit
sudo yum update -y  # For Amazon Linux
sudo apt update -y && sudo apt upgrade -y  # For Ubuntu
### 2️⃣ Install Python and Pip
sh
Copy
Edit
sudo yum install python3 -y  # For Amazon Linux
sudo apt install python3 python3-pip -y  # For Ubuntu
### 3️⃣ Install Git
sh
Copy
Edit
sudo yum install git -y  # Amazon Linux
sudo apt install git -y  # Ubuntu
## Step 4: Install Docker & Docker-Compose
### 1️⃣ Install Docker
sh
Copy
Edit
sudo yum install docker -y  # Amazon Linux
sudo apt install docker.io -y  # Ubuntu
Start and enable Docker:
sh
Copy
Edit
sudo systemctl start docker
sudo systemctl enable docker
### 2️⃣ Install Docker-Compose
sh
Copy
Edit
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
Verify installation:
sh
Copy
Edit
docker-compose --version
## Step 5: Set Up Milvus (Vector Database)
### 1️⃣ Clone the Milvus Repository
sh
Copy
Edit
git clone https://github.com/milvus-io/milvus.git
cd milvus
### 2️⃣ Create a Docker-Compose File
sh
Copy
Edit
nano docker-compose.yml
Paste the following:

yaml
Copy
Edit
version: '3.5'
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.0
    container_name: milvus-etcd
    ports:
      - "2379:2379"

  minio:
    image: minio/minio:RELEASE.2021-04-06T23-11-00Z
    container_name: milvus-minio
    ports:
      - "9000:9000"
    environment:
      MINIO_ACCESS_KEY: "minioadmin"
      MINIO_SECRET_KEY: "minioadmin"
    command: [ "server", "/data" ]

  milvus:
    image: milvusdb/milvus:v2.0.0
    container_name: milvus
    ports:
      - "19530:19530"
    depends_on:
      - etcd
      - minio
    environment:
      ETCD_ENDPOINTS: "milvus-etcd:2379"
      MINIO_ADDRESS: "minio:9000"
### 3️⃣ Start Milvus
sh
Copy
Edit
docker-compose up -d
Verify it's running:
sh
Copy
Edit
docker ps
## Step 6: Set Up FastAPI
### 1️⃣ Install Dependencies
sh
Copy
Edit
pip3 install pymilvus fastapi uvicorn pandas sentence-transformers
### 2️⃣ Clone Your Project Repository
sh
Copy
Edit
git clone <your-repo-url>
cd <your-repo-name>
### 3️⃣ Run Your FastAPI App
sh
Copy
Edit
python3 pymilvus_Test.py
OR Run it in the background:

sh
Copy
Edit
nohup python3 pymilvus_Test.py > app.log 2>&1 &
## Step 7: Test Your API
### 1️⃣ Find Your EC2 Public IP
In AWS EC2 Dashboard → Copy Public IPv4 address.
### 2️⃣ Test Your FastAPI Endpoint
Open your browser and go to:
bash
Copy
Edit
http://your-ec2-public-ip:8000/docs
You should see the Swagger UI where you can test API endpoints.
## Step 8: Set Up Auto-Restart (Optional)
### 1️⃣ Create a Systemd Service
sh
Copy
Edit
sudo nano /etc/systemd/system/fastapi.service
Add the following:

makefile
Copy
Edit
[Unit]
Description=FastAPI Service
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/<your-repo-name>
ExecStart=/usr/bin/python3 pymilvus_Test.py
Restart=always

[Install]
WantedBy=multi-user.target
### 2️⃣ Enable the Service
sh
Copy
Edit
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi
Check status:
sh
Copy
Edit
sudo systemctl status fastapi
## Step 9: Secure Your EC2 Instance
### 1️⃣ Enable a Firewall
sh
Copy
Edit
sudo yum install firewalld -y
sudo systemctl start firewalld
sudo systemctl enable firewalld
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
## Final Steps
✅ Milvus is running on EC2
✅ FastAPI is accessible at http://your-ec2-public-ip:8000/docs
✅ Your distributed vector database is ready! 🚀

Let me know if you need any help! 🎯