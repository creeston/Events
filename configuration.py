import os


def try_get_env(key):
    if key in os.environ:
        return os.environ[key]
    return None


tg_credentials = {
    "api_id": try_get_env("TG_API_ID"),
    "api_hash": try_get_env("TG_API_HASH")
}

vk_credentials = {
    "phone_num": try_get_env("VK_PHONE_NUM"),
    "password": try_get_env("VK_PASS")
}


cloudinary_config = {
  "cloud_name": try_get_env("CLOUD_NAME"),
  "api_key": try_get_env("CLOUD_API_KEY"),
  "api_secret": try_get_env("CLOUD_API_SECRET")
}

sql_server = {
    "server":  try_get_env("SQL_SERVER"),
    "database": try_get_env("SQL_DATABASE"),
    "username": try_get_env("SQL_USERNAME"),
    "password": try_get_env("SQL_PASS")
}

oauth = {
    "facebook": {
        "id": try_get_env("OAUTH_FB_ID"),
        "secret": try_get_env("OAUTH_FB_SECRET")
    }
}
