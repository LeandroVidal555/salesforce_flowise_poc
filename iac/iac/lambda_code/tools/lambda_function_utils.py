import os


# Get environment vars
common_prefix = os.getenv("COMMON_PREFIX")
env = os.getenv("ENV")
bucket_name = os.getenv("BUCKET_NAME")


def update_to_do_list(item):
    return []