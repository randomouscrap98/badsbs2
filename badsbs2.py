import logging
import requests
import getpass

# Load from a file sometime?
API = "https://newdev.smilebasicsource.com/api"

# Globals lol (this is a bad script!)
userId = 0
username = "" 
token = None

# Configure logging... you can change this I guess
logging.basicConfig(
    level=logging.DEBUG, 
    format='[%(asctime)s] %(message)s', 
    datefmt='%H:%M:%S')

def printHelp():
    print("""
* badsbs2: all commands are typed as-is *
    help
    login username
    logout
    token
    me
    quit
""")

def simpleformat(data):
    lines = []
    for k in data:
        lines.append(f" {k}: {data[k]}")
    return "\n".join(lines)

def stdheaders():
    global token
    headers = {"Accept" : "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def handleerror(response, failMessage = "API Fail"):
    logging.debug(response.text)
    message = ""
    try:
        data = response.json()
        if isinstance(data, str):
            message = data
        elif "errors" in data:
            for k in data["errors"]:
                message += k + ": " + ",".join(data["errors"][k])
    except:
        message = response.text
    raise Exception(f"{failMessage}: {message}")

def login(name):
    global username, userId, token
    if not name:
        raise Exception("Must provide username!")
    password = getpass.getpass(f"Password for {name}: ")
    logging.info(f"Logging in as {name}...")
    response = requests.post(f"{API}/user/authenticate", json = { "username" : name, "password" : password }, headers = stdheaders())
    if response:
        token = response.json()
        username = name
        logging.info("Login successful!")
    else:
        handleerror(response, "Could not login!")

def logout():
    global username, token
    username = ""
    token = None
    logging.info("Logged out!")

def stdrequest(url):
    logging.debug(f"GET: {url}")
    response = requests.get(url, headers = stdheaders())
    if response:
        return response.json()
    else:
        handleerror(response, "GET fail")

logging.info("Starting up...")
logging.info(f"Connecting to {API}...")

if requests.get(f"{API}/test"):
    logging.info("Connected!")
else:
    logging.critical("Could not connect, exiting...")
    exit(10)

printHelp()

# The command loop!
while True:
    try:
        read = input(f"{username}$ ")
        parts = read.strip().split(" ")
        command = parts[0].lower() if parts else ""

        if command == "quit":
            break
        elif command == "help":
            printHelp()
        elif command == "login":
            login(parts[1])
        elif command == "logout":
            logout()
        elif command == "token":
            print(f"Your token: {token}")
        elif command == "me":
            print(simpleformat(stdrequest(f"{API}/user/me")))

    except Exception as ex:
        logging.error(str(ex))

logging.info("Exiting!")

