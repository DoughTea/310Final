import requests
import json
import urllib.request, urllib.error, urllib.parse, json
from flask import Flask, render_template, request, session, redirect, url_for

def pretty(obj):
    return json.dumps(obj, sort_keys=True, indent=2)


from secret import CLIENT_ID, CLIENT_SECRET
GRANT_TYPE = 'authorization_code'

app = Flask(__name__)

app.secret_key = CLIENT_SECRET

### STUFF FOR SPOTIFY START####
    
### This adds a header with the user's access_token to Spotify requests
def spotifyurlfetch(url,access_token,params=None):
    headers = {'Authorization': 'Bearer '+access_token}
    req = urllib.request.Request(
        url = url,
        data = params,
        headers = headers
    )
    response = urllib.request.urlopen(req)
    return response.read()

### Handlers ###

### this will handle our home page
# WORK HERE 
@app.route("/")
def index():
    if 'user_id' in session:
        # if logged in, get their playlists

        # url = "https://api.spotify.com/v1/users/%s/playlists"%session['user_id']
        url = "	https://api.spotify.com/v1/me/top/artists?time_range=long_term&limit=50"
        # in the future, should make this more robust so it checks 
        # if the access_token is still valid and retrieves a new one
        # using refresh_token if not
        response = json.loads(spotifyurlfetch(url,session['access_token']))
        # playlists=response["items"]
        topArtists = response["items"]
    else:
        playlists = None
        topArtists = None
        
    return render_template('oauth.html',user=session,topArtists=topArtists)

### this handler will handle our authorization requests 
@app.route("/auth/login")
def login_handler():
    # after  login; redirected here      
    # did we get a successful login back?
    args = {}
    args['client_id']= CLIENT_ID
    
    verification_code = request.args.get("code")
    if verification_code:
        # if so, we will use code to get the access_token from Spotify
        # This corresponds to STEP 4 in https://developer.spotify.com/web-api/authorization-guide/
            
        args["client_secret"] = CLIENT_SECRET
        args["grant_type"] = GRANT_TYPE
        # store the code we got back from Spotify
        args["code"] = verification_code
        # the current page 
        args['redirect_uri'] = request.base_url    
        data = urllib.parse.urlencode(args).encode("utf-8")
        
        # We need to make a POST request, according to the documentation         
        #headers = {'content-type': 'application/x-www-form-urlencoded'}
        url = "https://accounts.spotify.com/api/token"
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req,data=data)
        response_dict = json.loads(response.read())
        access_token = response_dict["access_token"]
        refresh_token = response_dict["refresh_token"]

        # Download the user profile. Save profile and access_token
        # in Datastore; we'll need the access_token later
        
        ## the user profile is at https://api.spotify.com/v1/me
        profile = json.loads(spotifyurlfetch('https://api.spotify.com/v1/me',
            access_token))
        
        ## Put user info in session
        ## it is not generally a good idea to put all of this in 
        ## session, because there is a risk of sensitive info 
        ## (like access token) being exposed.
        session['user_id'] = profile["id"]   
        session['displayname'] = profile["display_name"]
        session['access_token'] = access_token
        session['profile_url'] = profile["external_urls"]["spotify"]
        session['api_url'] = profile["href"]
        session['refresh_token'] = refresh_token
        if profile.get('images') is not None:
            session['img'] = profile["images"][0]["url"]
        
        ## okay, all done, send them back to the App's home page
        return redirect(url_for('index'))
    else:
        # not logged in yet-- send the user to Spotify to do that
        # This corresponds to STEP 1 in https://developer.spotify.com/web-api/authorization-guide/
        
        args['redirect_uri']= request.base_url
        args['response_type']="code"
        #ask for the necessary permissions - 
        #see details at https://developer.spotify.com/web-api/using-scopes/
        args['scope']="user-library-modify playlist-modify-private playlist-modify-public playlist-read-collaborative playlist-read-private"
        
        url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(args)
        return redirect(url)

## this handler logs the user out by making the cookie expire
@app.route("/auth/logout")
def logout_handler():
    ## remove each key from the session!
    for key in list(session.keys()):
         session.pop(key)
    return redirect(url_for('index')) 

# END OF SPOTIFY STUFF


def get_song_data(search_term):
    client_access_token = "zfWrFxJwkxdCOTZDZ8rw3mi09_Yy6GFvVrro9-aElRzVcm0rThneQQrp9NSab7jt"

    search_term = search_term
    genius_search_url = f"http://api.genius.com/search?q={search_term}&access_token={client_access_token}"

    response = requests.get(genius_search_url)
    json_data = response.json()
    return json_data

def get_song_data_safe(search_term):
    try:
        return get_song_data(search_term)
    except urllib.error.HTTPError as e:
        app.logger.error("Error trying to retrieve data: %s"%e)
    except urllib.error.URLError as e:
        app.logger.error("We failed to reach a server.")
        app.logger.error("Reason: ", e.reason)
    return None

@app.route("/")
def main_handler():
    app.logger.info("In MainHandler")
    loc = request.args.get('loc')
    if loc:
        # if form filled in, greet them using this data
        songData = get_song_data_safe(loc)
        songs = []
        # songs has all the information for title and release date
        for song in songData["response"]["hits"]:
            songs.append([song["result"]["full_title"], song["result"]["release_date_components"]])
        print(songs)
        if songData is not None:
            title = "Which one came out first for %s?"%loc
            return render_template('homepagetemplate.html',
                page_title=title,
                songData=songData
                )
        else:
            return render_template('homepagetemplate.html',
                page_title="Artist Form - Error",
                prompt="Something went wrong with the API Call")                  
    elif loc=="":
        return render_template('homepagetemplate.html',
            page_title="Artist Form - Error",
            prompt="We need a artist name to search for!")
    else:
        return render_template('homepagetemplate.html',page_title="Sunrise Sunset Form")

def older(song1, song2):
    if song1[1]["year"] < song2[1]["year"]:
        return song1
    elif song1[1]["month"] < song2[1]["month"]:
        return song1


if __name__ == "__main__":
    # Used when running locally only. 
	# When deploying to Google AppEngine or PythonAnywhere,
    # a webserver process will serve your app. 
    app.run(host="localhost", port=8080, debug=True)#!/usr/bin/env python
from flask import Flask, render_template, request

