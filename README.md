# Webinterface for Adding Purchase Transactions to Beancount

## Install

Install cococount with
```bash
python3 setup.py install --user
```
where `--user` is an optional flag to install it for the current user only. If the installation of `systemd` fails, try (on Ubuntu):
```bash
sudo apt install build-essential libsystemd-dev
```

## Getting Started

Start the http and websocket server:
```bash
cococount-server <path>/<to>/example.beancount
```
Open the interface in the browser at http://localhost:8000/index.html . The transactions will be flushed to the file if the websocket server is interrupted, e.g. when stopping with Ctrl+C.
