from openhab.actions import HTTP

response = HTTP.sendHttpGetRequest("https://www.openhab.org/")

print(response)
