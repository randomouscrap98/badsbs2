## badsbs2
A python script that gives a very bad interface for sbs2

## Running
Get the whole repo, clone it, whatever.

If you're on linux, all you have to do to run is:

```shell
make run  
```

If you're not on linux, you should be

### Manual steps

I recommend just running make if possible. 
The manual steps for linux setup are:

```shell
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
deactivate
```

The manual steps for linux running (assuming you setup like above) are:

```shell
source .venv/bin/activate
python3 badsbs2.py
deactivate
```

