## badsbs2
A python script (singular) that gives a very bad interface for sbs2

## Running
Get the code, you need badsbs2.py and requirements.txt

You'll need to create/activate a virtual environment, restore the requirements, then you can run the script.
Always remember to activate the virtual environment you create before you run the script

On linux, the one-time setup might look like:
```shell
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
deactivate
```

On linux, running might look like:
```shell
source .venv/bin/activate
python3 badsbs2.py
deactivate
```

Or if on linux, you can just run some scripts (if you got them from the repo):
```shell
make      # sets up environment and whatever
make run  # runs the program in the environment
```
