import os


tg_credentials = {
    "api_id": int(os.environ["TG_API_ID"]),
    "api_hash": os.environ["TG_API_HASH"]
}

vk_credentials = {
    "phone_num": os.environ["VK_PHONE_NUM"],
    "password": os.environ["VK_PASS"]
}


cloudinary_config = {
  "cloud_name": os.environ["CLOUD_NAME"],
  "api_key": os.environ["CLOUD_API_KEY"],
  "api_secret": os.environ["CLOUD_API_SECRET"]
}

sql_server = {
    "server":  os.environ["SQL_SERVER"],
    "database": os.environ["SQL_DATABASE"],
    "username": os.environ["SQL_USERNAME"],
    "password": os.environ["SQL_PASS"]
}

print(sql_server)

oauth = {
    "facebook": {
        "id": os.environ["OAUTH_FB_ID"],
        "secret": os.environ["OAUTH_FB_SECRET"]
    }
}
