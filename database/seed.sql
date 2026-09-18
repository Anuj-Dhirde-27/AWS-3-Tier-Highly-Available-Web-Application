-- Demo data used by the AWS project during development.
-- Passwords are plaintext here to match the current learning implementation.
-- Replace with Werkzeug password hashes before production use.

INSERT INTO users (email, password_hash, role)
VALUES
('anuj-admin@example.com', 'YOUR_EXISTING_ADMIN_PASSWORD', 'admin'),
('user@example.com', 'user123', 'customer');

INSERT INTO products (name, description, price, stock)
VALUES
('Laptop', 'Business laptop', 65000, 10),
('Wireless Keyboard', 'Compact wireless keyboard', 2500, 20),
('Wireless Mouse', 'Ergonomic wireless mouse', 1500, 30),
('Monitor', '24-inch Full HD monitor', 12000, 8);
