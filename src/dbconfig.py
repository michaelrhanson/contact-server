import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Example values include 
#   "sqlite:///:memory:"
#   "sqlite:///local.db"

echo = False
if 'CONFIG_SQLALCHEMY_ECHO' in os.environ:
  echo = os.environ['CONFIG_SQLALCHEMY_ECHO'] == "true"

engine = create_engine(os.environ['CONFIG_SQLALCHEMY'], echo=echo)

Session = sessionmaker(bind=engine)


