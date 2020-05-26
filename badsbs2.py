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
    level=logging.INFO, 
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
    categories (#)
    quit
""")

def simpleformat(data):
    lines = []
    for k in data:
        lines.append(f" {k}: {data[k]}")
    return "\n".join(lines)

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
    raise Exception(f"({response.status_code}) {failMessage}: {message}")

def stdheaders():
    global token
    headers = {"Accept" : "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def stdrequest(url):
    logging.debug(f"GET: {url}")
    response = requests.get(url, headers = stdheaders())
    if response:
        return response.json()
    else:
        handleerror(response, "GET fail")

def computecategorytree(categories):
    root = {"id" : 0, "children" : [], "name" : "Root Categories", "myPerms" : "" }
    pending = [root]
    while pending:
        next = pending.pop()
        for c in categories:
            if c["parentId"] == next["id"] and next["id"] != c["id"]:
                next["children"].append(c)
                c["children"] = []
                pending.append(c)
    return root

def findnode(root, id):
    pending = [root]
    while pending:
        next = pending.pop()
        for c in next["children"]:
            pending.append(c)
        if next["id"] == id:
            return next
    raise Exception(f"No node found with id {id}!")

def printcattree(node, level):
    print((" " * level * 2) + str(node["id"]) + ": " + node["name"])
    for c in node["children"]:
        printcattree(c, level + 1)

def displaycategories(num):
    categories = stdrequest(f"{API}/category")
    root = computecategorytree(categories)
    node = findnode(root, num)
    printcattree(node, 0)

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
        elif command == "categories":
            displaycategories(int(parts[1]) if len(parts) > 1 else 0)

    except Exception as ex:
        logging.error(str(ex))

logging.info("Exiting!")

