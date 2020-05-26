import logging
import requests
import getpass
import timeago
import datetime
import dateutil.parser

# Load from a file sometime?
API = "https://newdev.smilebasicsource.com/api"
DISPLAYLIMIT = 20
INDENT = 2
LOGLEVEL = logging.INFO

# Globals lol (this is a bad script!)
userId = 0
username = "" 
token = None

# Configure logging... you can change this I guess
logging.basicConfig(
    level=LOGLEVEL, 
    format='[%(asctime)s] %(message)s', 
    datefmt='%H:%M:%S')

def printHelp():
    print("""
badsbs2: all commands are typed as-is
 ------------------------
  help
  login username
  logout
  token
  me
  categories (#)
  contents (parent#) (page#)
  quit 
 ------------------------
""".strip("\n"))

# A simple way to display a dictionary of data (warn: will print objects for any nested object)
def simpleformat(data):
    lines = []
    for k in data:
        lines.append(f" {k}: {data[k]}")
    return "\n".join(lines)

# def linkusers(list, users):
#     for l in list:
#         if "createUserId" in l:


# Assuming response is in an error state, "handle" it (based on our api)
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

# Get standard headers (authorize, etc)
def stdheaders():
    global token
    headers = {"Accept" : "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

# A standard GET request to any endpoint (includes authorization)
def stdrequest(url):
    logging.debug(f"GET: {url}")
    response = requests.get(url, headers = stdheaders())
    if response:
        return response.json()
    else:
        handleerror(response, "GET fail")

# Given a standard category result from the API, build a TREE
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

# Find a node with a given id in a tree (could be any tree with ids and children)
def findnode(root, id):
    pending = [root]
    while pending:
        next = pending.pop()
        for c in next["children"]:
            pending.append(c)
        if next["id"] == id:
            return next
    raise Exception(f"No node found with id {id}!")

def trimtree(root, removeCheck):
    # "depth first", go to the bottom and trim up
    if "children" in root:
        children = root["children"]
        root["children"] = []
        for c in children:
            val = trimtree(c, removeCheck)
            if val:
                root["children"].append(val)
    # Now check ourselves
    if removeCheck(root):
        return None
    else:
        return root


# Print a category tree hierarchy starting at node (recursive)
def printcattree(node, level = 0):
    if not node:
        return
    nextLevel = level
    if node["id"] != 0:
        output = (" " * level * INDENT) + str(node["id"]) + ": "
        if "username" in node:
            output += "[" + node["username"] + "] "
        output += node["name"]
        if "editDate" in node:
            output += " - " + timeago.format(dateutil.parser.parse(node["editDate"]), datetime.datetime.now(datetime.timezone.utc))
        print(output)
        nextLevel += 1
    if "children" in node:
        for c in node["children"]:
            printcattree(c, nextLevel)

# Called directly from command loop: do everything to display categories
def displaycategories(num):
    chain = stdrequest(f"{API}/read/chain?requests=category&category=id,name,parentId")
    root = computecategorytree(chain["category"])
    node = findnode(root, num)
    printcattree(node)

def displaycontent(parent, page):
    pstr = str(parent) if parent > 0 else ""
    skip = str(page * DISPLAYLIMIT)
    limit = str(DISPLAYLIMIT)
    chain = stdrequest(f"{API}/Read/chain?requests=content-%7B%22parentIds%22%3A%5B{pstr}%5D%2C%20%22limit%22%3A{limit}%2C%22skip%22%3A{skip}%2C%22sort%22%3A%22editDate%22%2C%22reverse%22%3Atrue%7D&requests=category&requests=user.0createUserId&category=id,name,parentId&content=id,name,createuserId,parentid,editDate&user=id,username")
    content = chain["content"] if "content" in chain else []
    for c in content:
        for u in chain["user"]:
            if u["id"] == c["createUserId"]:
                c["username"] = u["username"]
    all = chain["category"] + content
    tree = trimtree(computecategorytree(all), lambda x: "createUserId" not in x and len(x["children"]) == 0)
    if tree:
        printcattree(tree)
    else:
        logging.warning("No content")

# Called directly from command loop: do everything necessary to login
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

# Called directly from command loop: do everything necessary to logout
def logout():
    global username, token
    username = ""
    token = None
    logging.info("Logged out!")


# Beginning of real program: just leave everything lying around outside I guess...
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
        elif command == "contents":
            displaycontent(int(parts[1]) if len(parts) > 1 else -1, int(parts[2]) if len(parts) > 2 else 0)
        else:
            logging.warning(f"Unknown command: {command}")

    except Exception as ex:
        logging.error(str(ex))

logging.info("Exiting!")

