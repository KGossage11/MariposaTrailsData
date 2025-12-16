# MariposaTrailsData
---
## Repo Format
* Trail and post data stored in data.json
* Image and audio files stores in uploads/
* Version number stored in version.json
---
## App.py
* Holds API endpoints used by admin page and mobile app
  * /login
    * Used for admin page login
  * /
    * Main Page
  * /data
    * GET - returns contents of data.json
  * /version
    * GET - returns contents of version.json
  * /update
    * POST - updates contents of data.json and increments version.json by 1 
