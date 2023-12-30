# Example Package

This is a simple example package. You can use

To start working with this package
````
    my_db = PDB(host, user, password, dbname)
    my_db.FT.insert("m5.xlarge",100,"m5.xlarge")
    my_db.pod.insert("b6666wq-3nadsd","pod",1,0.5,2,1,"m5.xlarge")
````


To build and upload
````
python3 -m pip install --upgrade build
python3 -m build
export TWINE_USERNAME=aws
export TWINE_PASSWORD==`aws codeartifact get-authorization-token --domain placeless --domain-owner 945239671794 --query authorizationToken --output text`
export TWINE_REPOSITORY_URL=`aws codeartifact get-repository-endpoint --domain placeless --domain-owner 945239671794 --repository placeless-PDB --format pypi --query repositoryEndpoint --output text`
````
Download as pip package(linux):

```
aws codeartifact login --tool pip --repository placeless-private --domain placeless --domain-owner 945239671794
export CODEARTIFACT_AUTH_TOKEN=`aws codeartifact get-authorization-token --domain placeless --domain-owner 945239671794 --query authorizationToken --output text`
pip config set global.index-url https://aws:$CODEARTIFACT_AUTH_TOKEN@placeless-945239671794.d.codeartifact.us-east-1.amazonaws.com/pypi/placeless-private/simple/
``` 

```
pip install -i https://aws:$CODEARTIFACT_AUTH_TOKEN@placeless-945239671794.d.codeartifact.us-east-1.amazonaws.com/pypi/placeless-private/simple/ placeless-pdb
```
note: It can work without the `-i` flag, but if you run into problems in your local env, that sould solve it

Download as pip package(Windows):
```
1. aws codeartifact login --tool pip --repository placeless-private --domain placeless --domain-owner 945239671794
2. for /f %i in ('aws codeartifact get-authorization-token --domain placeless --domain-owner 945239671794 --query authorizationToken --output text') do set CODEARTIFACT_AUTH_TOKEN=%i

pip install placeless-pdb

```
