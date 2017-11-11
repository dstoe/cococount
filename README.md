# Webinterface for Adding Purchase Transactions to Beancount

## Getting Started

Start the websocket server:
```bash
python3 server.py data/example.beancount
```
Start the webserver:
```bash
cd www && python3 -m http.server 8000
```
Open the interface in the browser at http://localhost:8000 . The transactions will be flushed to the file if the websocket server is interrupted, e.g. when stopping with Ctrl+C.
