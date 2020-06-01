import logging
import requests
import getpass
import timeago
import datetime
import dateutil.parser
import os
import re
import json
import base64


# Load from a file sometime? Nah it's a script, just change it!
API = "https://newdev.smilebasicsource.com/api"
DISPLAYLIMIT = 20               # The max amount to display for any paged list
INDENT = 2                      # the indent for each level on tree views
LOGLEVEL = logging.INFO         # the minimum logging level
TOKENFILE = "token.secret"      # where to store login token (optional)

# Everything is globals lol (this is a bad script!)

# Set all the data surrounding a logged in user... kind of?
# Also note that token is JUST the token and not Bearer <token>
def setToken(t, name = None):
    global username, userId, token
    token = t
    if t:
        username = name
        part = (token.split(".")[1]).encode("UTF-8")
        raw = base64.decodebytes(part)
        userId = (json.loads(raw))["uid"]
    else:
        username = ""
        userId = 0

# Assume no login
setToken(None)

# Configure logging... you can change this I guess
logging.basicConfig(
    level=LOGLEVEL, 
    format='[%(asctime)s] %(message)s', 
    datefmt='%H:%M:%S')

def printHelp():
    print("""
badsbs2: all commands are typed as-is
| = "or", commands can be substituted
 ------------------------
  help 
  login username
  logout|token|me
  register username email
  confirm key
  categories (#)
  contents (parent#) (page#)
  comments parent# (page#)
  users|watches|activity (page#)
  category|content|user|watch #
  notifications (verbose)
  watch add|clear|delete #
  qcat|qcon|qcom parent#
  qconed #
  quit 
 ------------------------
""".strip("\n"))

# Return a simple english representation of time since the given (API-supplied) time
def timesince(date):
    return timeago.format(dateutil.parser.parse(date), datetime.datetime.now(datetime.timezone.utc))

# Return the maximum STRING WIDTH of the IDs in a result
def maxnumlen(list, field = "id"):
    return max({len(str(l[field])) for l in list })

# A simple way to display a dictionary of data (warn: will print objects for any nested object)
def simpleformat(data):
    lines = []
    maxwidth = len(max(data.keys(), key = len)) + 1
    for k in data:
        dk = (f"{k}:").rjust(maxwidth)
        lines.append(f" {dk} {data[k]}")
    return "\n".join(lines)

def yn(prompt):
    r = input(prompt + " (y/n): ")
    return r.lower() == "y"

# Simple linking for returned chained data
def link(orig: tuple, assoc: tuple, linkname):
    for o in orig[0]:
        for a in assoc[0]:
            if o[orig[1]] == a[assoc[1]]:
                o[linkname] = a

# Simple method to retrieve a pre-formatted (for the API) dictionary of permissions
def permget():
    p = input("Permissions (OCR 1CRUD): ")
    perms = {}
    for part in filter(None, p.split(" ")):
        match = re.match(r"(^\d+)([CcRrUuDd]+)$", part)
        if not match:
            logging.warning(f"Couldn't understand {part}, retry!")
            return permget()
        perms[match.group(1)] = match.group(2)
    return perms

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

# A standard GET request to any endpoint (includes authorization AND error checking)
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
def printcattree(node, level = 0, maxIdLen = 0):
    if not node:
        return
    nextLevel = level
    if node["id"] != 0:
        output = (" " * level * INDENT) + str(node["id"]).rjust(maxIdLen, "0") + ": "
        output += node["name"]
        if "user" in node:
            output += " [" + node["user"]["username"] + "]"
        if "editDate" in node:
            output += " - " + timesince(node["editDate"])
        print(output)
        nextLevel += 1
    if "children" in node:
        if node["children"]:
            maxIdLen = maxnumlen(node["children"])
        for c in node["children"]:
            printcattree(c, nextLevel, maxIdLen)

def simplelist(endpoint, page):
    skip = str(page * DISPLAYLIMIT)
    return stdrequest(f"{API}/{endpoint}?Limit={DISPLAYLIMIT}&skip={skip}")

def idresult(req, display, field = "id"):
    if req:
        maxIdLen = maxnumlen(req, field)
        for r in req:
            rid = str(r[field]).rjust(maxIdLen)
            print(f"{rid}: " + display(r))

# Called directly from command loop: do everything to display categories
def displaycategories(num):
    chain = stdrequest(f"{API}/read/chain?requests=category&category=id,name,parentId")
    root = computecategorytree(chain["category"])
    node = findnode(root, num)
    printcattree(node)

def displaycontents(parent, page):
    pstr = str(parent) if parent > 0 else ""
    skip = str(page * DISPLAYLIMIT)
    limit = str(DISPLAYLIMIT)
    chain = stdrequest(f"{API}/Read/chain?requests=content-%7B%22parentIds%22%3A%5B{pstr}%5D%2C%20%22limit%22%3A{limit}%2C%22skip%22%3A{skip}%2C%22sort%22%3A%22editDate%22%2C%22reverse%22%3Atrue%7D&requests=category&requests=user.0createUserId&category=id,name,parentId&content=id,name,createuserId,parentid,editDate&user=id,username")
    content = chain["content"] if "content" in chain else []
    link((content, "createUserId"), (chain["user"], "id"), "user")
    all = chain["category"] + content
    tree = trimtree(computecategorytree(all), lambda x: "createUserId" not in x and len(x["children"]) == 0)
    if tree:
        printcattree(tree)
    else:
        logging.warning("No content")

def displayusers(page):
    req = simplelist("user", page) 
    idresult(req, lambda x: f"{x['username']} - " + timesince(x["createDate"]))

def displaywatches(page):
    skip = str(page * DISPLAYLIMIT)
    req = stdrequest(f"{API}/read/chain?requests=watch-%7B%22Limit%22%3A{DISPLAYLIMIT}%2C%22skip%22%3A{skip}%7D&requests=content.0contentId")
    link((req["watch"], "contentId"), (req["content"], "id"), "content")
    idresult(req["watch"], lambda x: (f"{x['content']['name']} [C{x['content']['parentId']}:U{x['content']['createUserId']}]" if 'content' in x else '') + " - " + timesince(x["createDate"]), "contentId")

def displaycomments(contentid, page):
    skip = str(page * DISPLAYLIMIT)
    req = stdrequest(f"{API}/read/chain?requests=comment-%7B%22parentids%22%3A%5B{contentid}%5D%2C%22reverse%22%3Atrue%2C%22limit%22%3A{DISPLAYLIMIT}%2C%22skip%22%3A{skip}%7D&requests=user.0createUserId")
    link((req["comment"], "createUserId"), (req["user"], "id"), "user")
    maxUsername = max(len(u["username"]) for u in req["user"]) if req["user"] else 0
    idresult(req["comment"][::-1], lambda x: x['user']["username"].rjust(maxUsername) + ": " + json.loads(x['content'])["t"] + " - " + timesince(x["createDate"])) #[C{x['content']['parentId']}:U{x['content']['createUserId']}]" if 'content' in x else '') + " - " + timesince(x["createDate"]), "contentId")

# Notifications are, I assume, usually just a count. You could show more details somewhere else but like most of the time
# you just want a number. As such, we make a single request with two unrelated chains: aggregate activity and aggregate
# comments, but pass in a special search parameter "ContentLimit" : { "Watches" : true } to indicate we ONLY want the
# content that shows up in our watch list. If you're not logged in and request this, of course it will be empty. If there
# are no watches or no new comments, it is also empty. The special watch parameter also sets activity and comment id 
# limits based on the last time you cleared watch notifications so it will ONLY return EXACTLY the things which are...
# well, notifications. You can see that without verbose, for each content, it simply prints the activity aggregate count
# added to the comment aggregate count. Since there's no way to "combine" this in the API yet, it's also easy to display
# them separately (in verbose mode). So yes, notifications are just aggregate activity counts (watches only) plus 
# aggregate comment counts (watches only). You can simply add ALL the counts to get an overall number. These should be
# relatively performant but try not to call it all the time, if you HAVE to, maybe once a minute?
def displaynotifications(long = None):
    req = stdrequest(f"{API}/read/chain?requests=activityaggregate-%7B%22ContentLimit%22%20%3A%20%7B%20%22Watches%22%3Atrue%7D%7D&requests=commentaggregate-%7B%22ContentLimit%22%20%3A%20%7B%20%22Watches%22%3Atrue%7D%7D&requests=content.0Id.1Id&content=id,name,parentId,createUserId")
    link((req["content"], "id"), (req["activityaggregate"], "id"), "activity")
    link((req["content"], "id"), (req["commentaggregate"], "id"), "comment")
    def show(x):
        total = 0
        msg = ""
        if "activity" in x:
            a = x['activity']
            total += a['count']
            if long:
                msg += f"\n  {a['count']} activity - " + timesince(a["lastDate"])
        if "comment" in x:
            c = x['comment']
            total += c['count']
            if long: 
                msg += f"\n  {c['count']} comment - " + timesince(c["lastDate"])
        msg = f"{x['name']} [C{x['parentId']}:U{x['createUserId']}] : {total}" + msg
        return msg
    idresult(req["content"], show)

# So activity is interesting because it is events for ANY kind of thing OTHER than comments, which includes files, categories, content,
# and users (among other things in the future?). So you must chain the activity contentid against multiple things and link it all out 
# later. that's why there's both multiple chains AND multiple python linking AND the if/elif madness.
def displayactivity(page):
    skip = str(page * DISPLAYLIMIT)
    req = stdrequest(f"{API}/read/chain?requests=activity-%7B%22reverse%22%3Atrue%2C%22limit%22%3A{DISPLAYLIMIT}%2C%22skip%22%3A{skip}%7D&requests=content.0contentId&requests=user.0userId.0contentId&requests=category.0contentId&content=id,name,parentId,createUserId&user=id,username")
    req["user"].append({"id":-1,"username":"|SYSTEM|"})
    link((req["activity"], "contentId"), (req["content"], "id"), "content")
    link((req["activity"], "contentId"), (req["user"], "id"), "contentuser")
    link((req["activity"], "contentId"), (req["category"], "id"), "contentcategory")
    link((req["activity"], "userId"), (req["user"], "id"), "user")
    def show(x):
        msg = x["user"]["username"] if "user" in x else "???"
        msg += " " + {"c":"created","d":"deleted","r":"read","u":"updated"}[x["action"]]
        msg += " " + x["type"]
        if "content" in x:
            c = x["content"]
            msg += f" {c['name']} [I{c['id']}:C{c['parentId']}:U{c['createUserId']}]" 
        elif "contentuser" in x:
            c = x["contentuser"]
            msg += f" {c['username']} [{c['id']}]" 
        elif "contentcategory" in x:
            c = x["contentcategory"]
            msg += f" {c['name']} [{c['id']}]" 
        else:
            msg += " " + x["extra"]
        msg += " " + timesince(x["date"])
        return msg
    idresult(req["activity"], show)

def qcat(parent):
    category = { "parentId" : parent }
    category["name"] = input("Category name: ")
    category["description"] = input("Category description: ")
    category["permissions"] = permget()
    response = requests.post(f"{API}/category", json = category, headers = stdheaders())
    if response:
        print(simpleformat(response.json()))
    else:
        handleerror(response, "POST fail")

def qcon(parent):
    content = { "parentId" : parent }
    content["name"] = input("Content name: ")
    content["content"] = input("Content: ")
    content["permissions"] = permget()
    content["type"] = "@page.resource"
    content["values"] = { "markupLang": "plaintext", "photos": "" }
    response = requests.post(f"{API}/content", json = content, headers = stdheaders())
    if response:
        print(simpleformat(response.json()))
    else:
        handleerror(response, "POST fail")

def qcom(parent):
    comment = { "parentId" : parent }
    comment["content"] = json.dumps({ "m" : "plaintext", "t" : input("Comment: ") })
    response = requests.post(f"{API}/comment", json = comment, headers = stdheaders())
    if response:
        print(simpleformat(response.json()))
    else:
        handleerror(response, "POST fail")

def qconed(content):
    response = stdrequest(f"{API}/content?ids={content}")[0]
    response["values"]["badsbs2"] = str(int(datetime.datetime.utcnow().timestamp()))
    response2 = requests.put(f"{API}/content/{content}", json = response, headers = stdheaders())
    if response:
        print(simpleformat(response2.json()))
    else:
        handleerror(response2, "POST fail")

def watchcmd(cmd, id):
    if cmd == "add":
        response = requests.post(f"{API}/watch/{id}", headers = stdheaders())
        if response:
            print(simpleformat(response.json()))
        else:
            handleerror(response, "Watch fail")
    elif cmd == "clear":
        response = requests.post(f"{API}/watch/{id}/clear", headers = stdheaders())
        if response:
            print(simpleformat(response.json()))
            logging.info(f"Cleared notifications for content {id}")
        else:
            handleerror(response, "Watch fail")
    elif cmd == "delete":
        response = requests.delete(f"{API}/watch/{id}", headers = stdheaders())
        if response:
            print(simpleformat(response.json()))
            logging.info(f"Deleted watch for content {id}")
        else:
            handleerror(response, "Watch fail")
    else:
        logging.warning(f"Unknown watch command {cmd}")


# Called directly from command loop: do everything necessary to login
def login(name):
    if not name:
        raise Exception("Must provide username!")
    password = getpass.getpass(f"Password for {name}: ")
    logging.info(f"Logging in as {name}...")
    response = requests.post(f"{API}/user/authenticate", json = { "username" : name, "password" : password }, headers = stdheaders())
    if response:
        t = response.json()
        setToken(t, name)
        logging.info("Login successful!")
        if yn("Store login token for automatic login?"):
            with open(TOKENFILE, "w") as f:
                f.write(t)
    else:
        handleerror(response, "Could not login!")

def register(name, email):
    if not name:
        raise Exception("Must provide username!")
    if not email:
        raise Exception("Must provide email!")
    password = getpass.getpass(f"Register password for {name}: ")
    logging.info(f"Performing initial registration for {name}...")
    response = requests.post(f"{API}/user/register", json = { "username" : name, "password" : password, "email": email }, headers = stdheaders())
    if response:
        logging.info(f"Registration successful! Sending email to {email}...")
        response2 = requests.post(f"{API}/user/register/sendemail", json = {"email":email}, headers = stdheaders())
        if response2:
            logging.info("Sent registration email!")
        else:
            handleerror(response, "Could not send email!")
    else:
        handleerror(response, "Could not register!")

def confirm(key):
    if not key:
        raise Exception("Must provide key!")
    logging.info(f"Confirming key...")
    response = requests.post(f"{API}/user/register/confirm", json = { "confirmationKey" : key }, headers = stdheaders())
    if response:
        logging.info("User confirmed! Hope you remember who it was!")
    else:
        handleerror(response, "Could not confirm key!")

# Called directly from command loop: do everything necessary to logout
def logout():
    setToken(None)
    if os.path.isfile(TOKENFILE):
        os.remove(TOKENFILE)
        logging.info("Removed cached login")
    logging.info("Logged out!")


# Beginning of real program: just leave everything lying around outside I guess...
logging.info("Starting up...")
logging.info(f"Connecting to {API}...")

if requests.get(f"{API}/test"):
    logging.info("Connected!")
else:
    logging.critical("Could not connect, exiting...")
    exit(10)

if os.path.isfile(TOKENFILE):
    logging.info("Found existing login... trying now")
    with open(TOKENFILE, "r") as f:
        token = f.read()
    # now test the token
    me = stdrequest(f"{API}/user/me")
    if me:
        logging.info("Pre-existing login valid!")
        setToken(token, me["username"])

printHelp()

# The command loop!
while True:
    try:
        read = input(f"{username}[{userId}]$ ")
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
        elif command == "register":
            register(parts[1], parts[2])
        elif command == "confirm":
            confirm(parts[1])
        elif command == "me":
            print(simpleformat(stdrequest(f"{API}/user/me")))
        elif command == "category":
            print(simpleformat(stdrequest(f"{API}/category?ids={parts[1]}")[0]))
        elif command == "content":
            print(simpleformat(stdrequest(f"{API}/content?ids={parts[1]}")[0]))
        elif command == "user":
            print(simpleformat(stdrequest(f"{API}/user?ids={parts[1]}")[0]))
        elif command == "watch" and (len(parts) == 1 or len(parts) == 2 and parts[1].isnumeric()):
            print(simpleformat(stdrequest(f"{API}/watch?contentids={parts[1]}")[0]))
        elif command == "categories":
            displaycategories(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "contents":
            displaycontents(int(parts[1]) if len(parts) > 1 else -1, int(parts[2]) if len(parts) > 2 else 0)
        elif command == "comments":
            displaycomments(int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        elif command == "users":
            displayusers(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "watches":
            displaywatches(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "activity":
            displayactivity(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "notifications":
            displaynotifications(parts[1] if len(parts) > 1 and (parts[1].lower() == "true" or parts[1].lower() == "verbose") else None) #int(parts[1]) if len(parts) > 1 else 0)
        elif command == "qcat":
            qcat(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "qcon":
            qcon(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "qcom":
            qcom(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "qconed":
            qconed(int(parts[1]) if len(parts) > 1 else 0)
        elif command == "watch":
            watchcmd(parts[1], parts[2])
        else:
            logging.warning(f"Unknown command: {command}")

    except Exception as ex:
        logging.error(str(ex))

logging.info("Exiting!")

