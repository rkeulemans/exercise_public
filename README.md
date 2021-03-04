# exercise_public
Using virtualenv:

Install virtualenv:
```bash
pip3 install virtualenv
```

Create a new virtual environment called `exercise` and install requirements:
```bash
virtualenv exercise
source exercise/bin/activate
pip3 install -r requirements.txt
```

Add the virtualenv to jupyter-notebook (when running locally):
```
python3 -m ipykernel install --user --name=exercise
```
