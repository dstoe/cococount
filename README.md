# Webinterface for Adding Purchase Transactions to Beancount

## Getting Started

Start the http and websocket server:
```bash
python3 server.py data/example.beancount
```
Open the interface in the browser at http://localhost:8000/index.html . The transactions will be flushed to the file if the websocket server is interrupted, e.g. when stopping with Ctrl+C.
