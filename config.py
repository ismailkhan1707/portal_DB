class Config:
    # SECRET_KEY is used to encrypt session cookies (login sessions)
    # Change 'mysecretkey' to any random string you like
    SECRET_KEY = 'iambatman'
    
    # These are your MySQL connection details
    MYSQL_HOST = 'localhost'       # MySQL is running on your own computer
    MYSQL_USER = 'root'            # Default MySQL username
    MYSQL_PASSWORD = 'sonofkhan@17' # The password you set when installing MySQL
    MYSQL_DB = 'portal_db'         # The database we just created