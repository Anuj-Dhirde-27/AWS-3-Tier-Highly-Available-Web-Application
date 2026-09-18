# AWS 3-Tier Highly Available Web Application

A traditional three-tier e-commerce application deployed on AWS to demonstrate hands-on cloud networking, load balancing, multi-AZ compute, private database connectivity, S3-based deployment, IAM, HTTPS, DNS, and PostgreSQL-backed application workflows.

## Demo Video

[🎬 Watch the Demo Video](INSERT_GDRIVE_LINK_HERE)

## Project Highlights

- Product catalogue backed by Amazon RDS for PostgreSQL
- User authentication and session-based login
- Shopping cart and checkout workflow
- Persistent orders and order items
- Inventory management and admin dashboard
- Application health endpoint at `/health`
- Two EC2 application servers across Availability Zones
- Application Load Balancer for request distribution
- HTTPS termination using AWS Certificate Manager
- Custom DNS using Amazon Route 53
- Private EC2-to-S3 access through an S3 Gateway VPC Endpoint
- IAM role for EC2 access to the deployment bucket

## Architecture

```text
                         Internet
                            |
                            v
                    Amazon Route 53
                            |
                            v
                 HTTPS / ACM Certificate
                            |
                            v
              Application Load Balancer
               Public Subnet - AZ 1 / AZ 2
                    /                \
                   /                  \
                  v                    v
          EC2 Application 1     EC2 Application 2
             AZ 1 Private          AZ 2 Private
                  \                    /
                   \                  /
                    v                v
                 Amazon RDS PostgreSQL
                    Private DB Tier

Deployment / package flow:

EC2 -> S3 Gateway VPC Endpoint -> Amazon S3

Temporary outbound dependency flow:

Private EC2 -> NAT Gateway -> Internet Gateway -> Internet
```

The verified implementation uses **two EC2 instances behind the ALB**. An Auto Scaling Group was not created as part of the documented implementation.

## AWS Components

| Component | Purpose |
|---|---|
| Amazon VPC | Isolated network boundary |
| Public subnets | Host the internet-facing ALB |
| Private application subnets | Host EC2 application servers |
| Private database subnets | Database-tier network placement |
| Internet Gateway | Internet connectivity for public routing |
| Route Tables | Control subnet traffic paths |
| Application Load Balancer | Distributes client traffic to EC2 |
| Target Group | Registers the EC2 application targets |
| Amazon EC2 | Runs the Flask application |
| NAT Gateway | Temporary outbound internet access |
| Amazon S3 | Stores the application ZIP package |
| S3 Gateway VPC Endpoint | Private EC2-to-S3 access |
| IAM Role | Authorizes EC2 access to S3 |
| Amazon RDS PostgreSQL | Persistent relational database |
| AWS Certificate Manager | Provides the HTTPS certificate |
| Amazon Route 53 | Resolves the custom domain |

## Application Stack

- **Backend:** Python / Flask
- **ORM:** Flask-SQLAlchemy
- **Database driver:** psycopg2-binary
- **Configuration:** python-dotenv
- **Database:** PostgreSQL on Amazon RDS
- **Frontend:** HTML, Jinja2 templates, CSS
- **Runtime:** Python virtual environment

There is no `package.json` because the project does not use a Node.js build system or JavaScript package manager. The frontend is server-rendered with Flask/Jinja2 and uses a single CSS file.

## Folder Structure

```text
AWS-3-Tier-Highly-Available-Web-Application/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── database/
│   ├── schema.sql
│   └── seed.sql
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── product.html
│   ├── cart.html
│   ├── orders.html
│   └── admin.html
└── static/
    └── style.css
```

## Local Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AWS-3-Tier-Highly-Available-Web-Application
```

### 2. Create a virtual environment

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and provide the PostgreSQL connection values:

```bash
cp .env.example .env
```

Example:

```text
FLASK_SECRET_KEY=replace-with-a-long-random-secret
DB_HOST=your-rds-endpoint.amazonaws.com
DB_PORT=5432
DB_NAME=ecommerce
DB_USER=postgres
DB_PASSWORD=your-rds-password
```

**Do not commit `.env` to GitHub.** It is excluded by `.gitignore`.

### 5. Create the database schema

Connect to PostgreSQL and run:

```bash
psql -h <RDS_ENDPOINT> -p 5432 -U <DB_USER> -d ecommerce -f database/schema.sql
```

Then insert the required demo records using `database/seed.sql`, replacing the placeholder admin password with your existing development credential.

### 6. Run the application

```bash
python app.py
```

The application listens on:

```text
http://127.0.0.1:8080
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

Expected response:

```text
OK
```

## AWS Deployment Notes

### Application Load Balancer

The target group uses:

```text
Protocol: HTTP
Port: 8080
Health check path: /health
```

The ALB is associated with the two public presentation subnets. The EC2 security group permits application traffic from the ALB security group on TCP/8080.

### RDS

The application connects to PostgreSQL using the environment variables in `.env`. The RDS security group allows TCP/5432 from the EC2 application security group.

### S3 Deployment

The application package can be uploaded to Amazon S3 and downloaded from EC2 through the S3 Gateway VPC Endpoint. The EC2 instance uses an IAM role rather than hard-coded AWS access keys.

### HTTPS and DNS

The custom domain is resolved through Route 53. The ALB terminates HTTPS using an ACM certificate on port 443 and forwards application traffic to the EC2 target group.

## Application Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Product catalogue |
| `/login` | GET, POST | User authentication |
| `/logout` | GET | Clear session |
| `/product/<id>` | GET | Product details |
| `/cart` | GET | View cart |
| `/cart/add/<id>` | POST | Add product to cart |
| `/cart/remove/<id>` | POST | Remove product |
| `/checkout` | POST | Create order and decrement inventory |
| `/orders` | GET | Customer order history |
| `/admin` | GET | Admin inventory and order view |
| `/admin/product/<id>/stock` | POST | Update product stock |
| `/health` | GET | ALB health check |

## Database Model

```text
users
  |
  +----< orders
             |
             +----< order_items >---- products
```

Tables:

- `users` — application users and roles
- `products` — catalogue items and current stock
- `orders` — customer order headers
- `order_items` — products and quantities belonging to each order

## Checkout Flow

1. The authenticated customer submits the cart to `/checkout`.
2. The application reloads product records from RDS.
3. Current stock is validated before creating the order.
4. An order record is created.
5. Order-item records are created for each product.
6. Inventory is decremented.
7. The SQLAlchemy transaction is committed.
8. The session cart is cleared.
9. The user is redirected to order history.

## Security Notes

This repository represents the hands-on learning implementation. Before production use, make these changes:

- Store password hashes using Werkzeug `generate_password_hash` and validate with `check_password_hash`.
- Store the Flask secret in a secure secret-management system.
- Store database credentials in AWS Secrets Manager or another secure secret store rather than a local `.env` on the server.
- Add CSRF protection to state-changing forms.
- Use HTTPS end-to-end where appropriate.
- Restrict security-group rules to the minimum required ports and sources.
- Use database transactions/locking or another concurrency strategy for high-volume inventory updates.
- Deploy the application with a production WSGI server such as Gunicorn and manage it with a service manager.
- Consider an Auto Scaling Group for dynamic application capacity.

## Cost / Learning Configuration

The project was built as a hands-on AWS learning environment. RDS was configured as a low-cost Single-AZ deployment rather than a production Multi-AZ database. NAT Gateway usage was used for required outbound dependency installation and private-subnet connectivity during the build.

## Author

**Anuj Dhirde**

AWS Certified Solutions Architect – Associate | Cloud / Network Engineering
