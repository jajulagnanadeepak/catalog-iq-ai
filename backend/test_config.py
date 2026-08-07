from config import settings

print("MongoDB URL:", settings.mongodb_url)
print("Database:", settings.database_name)
print("JWT Secret:", settings.jwt_secret)