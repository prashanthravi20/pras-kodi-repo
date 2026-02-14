# Credits https://github.com/humla/
# Credits https://github.com/reasonsrepo/
# Credits https://github.com/eintamil/

import base64
import datetime
import json
import re
import requests
import sys
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc

# py_2x_3x
import html
import urllib.error
import urllib.parse
import urllib.request

# py_2x_3x
# import HTMLParser
# from six.moves import urllib

# Get the plugin url in plugin:// notation.
URL = sys.argv[0]
# Get a plugin handle as an integer number.
HANDLE = int(sys.argv[1])

__settings__ = xbmcaddon.Addon(id="plugin.video.einthusan")
BASE_URL = __settings__.getSetting("base_url")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
)
CDN_PREFIX = "cdn"
CDN_ROOT = ".io"
CDN_BASE_URL = "einthusan" + CDN_ROOT


def safe_get(url, **kwargs):
    """Wrapper around requests.get that returns text or empty string and logs errors."""
    try:
        r = requests.get(url, timeout=10, **kwargs)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        addLog(f"HTTP GET error: {e}", "error")
        return ""


def safe_post(url, data=None, **kwargs):
    try:
        r = requests.post(url, data=data, timeout=10, **kwargs)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        addLog(f"HTTP POST error: {e}", "error")
        return ""


def build_plugin_url(params):
    """Build plugin URL from a params dict and return full plugin URL string."""
    return URL + "?" + urllib.parse.urlencode(params, doseq=True)


def create_listitem(title, image, isUhd=False):
    """Create a preconfigured xbmcgui.ListItem for a movie entry."""
    movieTitle = title + "[COLOR blue] - Ultra HD[/COLOR]" if isUhd else title
    listitem = xbmcgui.ListItem(movieTitle)
    listitem.setArt({"icon": "DefaultFolder.png", "thumb": image})
    vinfo = listitem.getVideoInfoTag()
    vinfo.setMediaType('video')
    vinfo.setTitle(movieTitle)
    return listitem, vinfo


# locationStr = xbmcplugin.getSetting(HANDLE, 'location')
# Locations = ['San Francisco', 'Dallas', 'Washington, D.C.',
#              'Toronto', 'London', 'Sydney', 'No Preference']

# locationId = int(locationStr)
# if (locationId > len(Locations) - 1):
#     locationId = len(Locations) - 1

# location = Locations[locationId]


def addLog(message, level="notice"):
    if level == "error":
        xbmc.log(str(message), level=xbmc.LOGERROR)
    else:
        xbmc.log(str(message), level=xbmc.LOGINFO)


def addDir(
    name,
    url,
    mode,
    image,
    lang="",
    description="",
    imdbId="",
    movieReleaseYear=0,
    isplayable=False,
    isUhd=False,
):
    params = {
        "url": url,
        "mode": str(mode),
        "name": name,
        "lang": lang,
        "description": description,
    }
    u = build_plugin_url(params)

    xbmcplugin.setContent(HANDLE, 'movies')
    listitem, vinfo = create_listitem(name, image, isUhd)

    isfolder = True
    if isplayable:
        isfolder = False
        vinfo.setMediaType('movie')
        listitem.setProperty("IsPlayable", "true")
        try:
            if not imdbId:
                movie_data = getMovieDataByMovieTitleFromTMDB(name, movieReleaseYear, lang)
            else:
                movie_data = getMovieDataFromTMDB(imdbId)
        except Exception as e:
            addLog(f"TMDB lookup failed: {e}", "error")
            vinfo.setPlot(description)
            vinfo.setGenres(["Drama"])
            try:
                vinfo.setYear(int(movieReleaseYear))
            except Exception:
                pass
            listitem.setArt({"fanart": image})
        else:
            setVideoInfo(listitem, movie_data, vinfo, image, description, movieReleaseYear)

    ok = xbmcplugin.addDirectoryItem(HANDLE, url=u, listitem=listitem, isFolder=isfolder)
    return ok

def setVideoInfo(listitem, movie_data, vinfo, image, movie_description, movieReleaseYear):
    # Extract Fanart URL
    fanart_path = movie_data.get('backdrop_path')
    if not fanart_path:
        fanArt = image
    else:
        fanArt = f'https://image.tmdb.org/t/p/original{fanart_path}'
    listitem.setArt({"fanart": fanArt})

    vinfo.setYear(int(movieReleaseYear))
    vinfo.setRating(movie_data['vote_average'], movie_data['vote_count'])

    plot = movie_data['overview']
    if plot == '':
        plot = movie_description
    vinfo.setPlot(plot)
    vinfo.setOriginalTitle(movie_data['original_title'])

    # Convert JSON data to a Python object
    genreTempStr = str(movie_data["genres"])
    genreTempStr = genreTempStr.replace("'", '"')
    genresObjArray = json.loads(genreTempStr)
    genresArray = [genre["name"] for genre in genresObjArray]
    if len(genresArray)==0:
        genresArray = ['Drama']
    vinfo.setGenres(genresArray)

    durationMin = movie_data['runtime']

    vinfo.setDuration(durationMin*60)
    vinfo.setIMDBNumber(movie_data['imdb_id'])


def get_params():
    """Parse the plugin query string into a dict of single values.

    Returns a mapping of parameter name -> value (strings).
    """
    param = {}
    try:
        paramstring = sys.argv[2]
    except Exception:
        return param

    if not paramstring:
        return param

    cleaned = paramstring.lstrip('?')
    # parse_qs returns lists for each key; keep only first value
    parsed = urllib.parse.parse_qs(cleaned, keep_blank_values=True)
    for k, v in parsed.items():
        if isinstance(v, list) and len(v) > 0:
            param[k] = v[0]
        else:
            param[k] = v
    return param

def getMovieDataFromTMDB(imdbId):
    # Your TMDb API key
    API_KEY = __settings__.getSetting("tmdb_api_key")
    IMDB_ID = imdbId  # Example IMDb ID for "The Shawshank Redemption"

    # Step 1: Convert IMDb ID to TMDb ID
    url = f'https://api.themoviedb.org/3/find/{IMDB_ID}?api_key={API_KEY}&external_source=imdb_id'
    response = requests.get(url)
    data = response.json()

    # Extract the TMDb ID
    tmdb_id = data['movie_results'][0]['id']

    # Step 2: Fetch Movie Details using TMDb ID
    movie_url = f'https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={API_KEY}'
    movie_response = requests.get(movie_url)
    movie_data = movie_response.json()
    # addLog(movie_data)

    return movie_data


def getMovieDataByMovieTitleFromTMDB(movieTitle, movieReleaseYear, language):
    API_KEY = __settings__.getSetting("tmdb_api_key")
    movie_name = movieTitle

    # Step 1: Search for the movie
    search_url = f'https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={movie_name}&primary_release_year={movieReleaseYear}'
    response = requests.get(search_url)
    search_results = response.json()

    if search_results['results']:
        # Filter movies in the selected language
        filtered_movies = [movie for movie in search_results['results'] if movie['original_language'] == language[:2]]
        if len(filtered_movies) > 1:
            raise Exception("More than one results returned")
        movie_id = filtered_movies[0]['id']

        # Step 2: Get movie details using the movie ID
        movie_url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}'
        movie_response = requests.get(movie_url)
        movie_data = movie_response.json()

        return movie_data
    else:
        raise Exception("No results returned")


def select_lang(name, url, language, mode):
    addLog("BASE_URL: " + BASE_URL)
    languages = [
        ("tamil", "", "Tamil"),
        ("hindi", "", "Hindi"),
        ("telugu", "", "Telugu"),
        ("malayalam", "", "Malayalam"),
        ("kannada", "", "Kannada"),
        ("bengali", "", "Bengali"),
        ("marathi", "", "Marathi"),
        ("punjabi", "", "Punjabi"),
    ]
    lang_pattern = r'<li><a href=".*?\?lang=(.+?)"><div.*?div><img src="(.+?)"><p class=".*?-bg">(.+?)</p>'
    html1 = safe_get(BASE_URL)
    if not html1:
        addLog("check BASE_URL", "error")
        xbmcgui.Dialog().ok(
            "Base URL Error",
            "Please check and update the Base URL in Addon Settings and restart the addon.",
        )
    else:
        lang_matches = re.findall(lang_pattern, html1)
        if len(lang_matches) == 0:
            addLog("check lang_pattern", "error")
        else:
            languages = lang_matches
    for lang_item in languages:
        lang = str(lang_item[0])
        title = str(lang_item[2])
        if "http" not in lang_item[1] and lang_item[1] != "":
            image = "https://" + str(lang_item[1])
        else:
            image = ""
        addDir(title, "", 1, image, lang)
    addDir("Addon Settings", "", 2, "DefaultAddonService.png", "")
    xbmcplugin.endOfDirectory(HANDLE)


def select_menu(name, url, language, mode):
    postData = "lang=" + language
    addDir(
        "Featured",
        BASE_URL + "/movie/browse/?" + postData,
        3,
        "DefaultAddonsRecentlyUpdated.png",
        language,
    )
    addDir(
        "Recently Added",
        BASE_URL + "/movie/results/?find=Recent&" + postData,
        11,
        "DefaultRecentlyAddedMovies.png",
        language,
    )
    addDir(
        "Most Watched",
        BASE_URL + "/movie/results/?find=Popularity&ptype=View&tp=l30d&" + postData,
        11,
        "DefaultMovies.png",
        language,
    )
    addDir(
        "Staff Picks",
        BASE_URL + "/movie/results/?find=StaffPick&" + postData,
        11,
        "DefaultDirector.png",
        language,
    )
    addDir(
        "A-Z",
        BASE_URL + "/movie/results/?" + postData,
        4,
        "DefaultMovieTitle.png",
        language,
    )
    addDir(
        "Year",
        BASE_URL + "/movie/results/?" + postData,
        5,
        "DefaultYear.png",
        language,
    )
    addDir(
        "Rating",
        BASE_URL + "/movie/results/?" + postData,
        8,
        "DefaultGenre.png",
        language,
    )
    addDir(
        "Actors",
        BASE_URL + "/movie/browse/?" + postData,
        12,
        "DefaultActor.png",
        language,
    )
    addDir(
        "Composer",
        BASE_URL + "/movie/browse/?" + postData,
        12,
        "DefaultArtist.png",
        language,
    )
    addDir(
        "Director",
        BASE_URL + "/movie/browse/?" + postData,
        12,
        "DefaultDirector.png",
        language,
    )
    addDir(
        "Search",
        BASE_URL + "/movie/results/?" + postData,
        9,
        "DefaultAddonsSearch.png",
        language,
    )

    xbmcplugin.endOfDirectory(HANDLE)


def select_settings(name, url, language, mode):
    __settings__.openSettings()


def menu_alpha(name, url, language, mode):
    addDir("Numbers", url + "&find=Numbers", 11, "")
    azlist = map(chr, list(range(65, 91)))
    for letter in azlist:
        addDir(letter, url + "&find=Alphabets&alpha=" + letter, 11, "")
    xbmcplugin.endOfDirectory(HANDLE)


def menu_years(name, url, language, mode):
    addDir("Decade", url, 6, "DefaultYear.png")
    addDir("Years", url, 7, "DefaultYear.png")
    xbmcplugin.endOfDirectory(HANDLE)


def submenu_decade(name, url, language, mode):
    postData = url + "&find=Decade&decade="
    values = [
        repr(x) for x in reversed(list(range(1940, datetime.date.today().year + 1, 10)))
    ]
    for attr_value in values:
        if attr_value is not None:
            addDir(
                str(attr_value) + "s", postData +
                str(attr_value), 11, "DefaultYear.png"
            )
    xbmcplugin.endOfDirectory(HANDLE)


def submenu_years(name, url, language, mode):
    postData = url + "&find=Year&year="
    values = [
        repr(x) for x in reversed(list(range(1940, datetime.date.today().year + 1)))
    ]
    for attr_value in values:
        if attr_value is not None:
            addDir(attr_value, postData + str(attr_value), 11, "DefaultYear.png")
    xbmcplugin.endOfDirectory(HANDLE)


def menu_rating(name, url, language, mode):
    postData = url + "&find=Rating"
    addDir(
        "Action (4+ stars)",
        postData + "&action=4&comedy=0&romance=0&storyline=0&performance=0&ratecount=1",
        11,
        "",
    )
    addDir(
        "Comedy (4+ stars)",
        postData + "&action=0&comedy=4&romance=0&storyline=0&performance=0&ratecount=1",
        11,
        "",
    )
    addDir(
        "Romance (4+ stars)",
        postData + "&action=0&comedy=0&romance=4&storyline=0&performance=0&ratecount=1",
        11,
        "",
    )
    addDir(
        "Storyline (4+ stars)",
        postData + "&action=0&comedy=0&romance=0&storyline=4&performance=0&ratecount=1",
        11,
        "",
    )
    addDir(
        "Performance (4+ stars)",
        postData + "&action=0&comedy=0&romance=0&storyline=0&performance=4&ratecount=1",
        11,
        "",
    )
    xbmcplugin.endOfDirectory(HANDLE)


def menu_cast(name, url, language, mode):
    if (name == 'Actors'):
        values = get_cast_helper(url, '', language)
    elif (name == 'Composer'):
        values = get_cast_helper(
            url, 'MUSIC_DIRECTOR', language)
    else:
        values = get_cast_helper(url, 'DIRECTOR', language)

    postData = "lang=" + language
    for val in values:
        addDir(val['name'], BASE_URL+'/movie/results/?' + postData +
               '&find=Cast&id='+val['actorid'] + '&role='+val['role'], 11, val['image'])

    xbmcplugin.endOfDirectory(HANDLE)


def get_cast_helper(url, attr, language):
    html = safe_get(url)
    match = re.compile(r'<a href="/movie/results/\?find=Cast.*?id=(.*?)&amp;lang=.*?role=(.*?)"><img.*?src="(.*?)">.*?<label>(.*?)</label>').findall(html)
    # Bit of a hack
    castlist = []
    for actorid, role, image, name in match:
        if 'http' not in image:
            image = 'http:' + image
        if (role == attr):
            castlist.append(
                {'actorid': actorid, 'role': role, 'image': image, 'name': name})

    return castlist


def menu_search(name, url, language, mode):
    keyb = xbmc.Keyboard("", "Search")
    keyb.doModal()
    if keyb.isConfirmed():
        search_term = urllib.parse.quote_plus(keyb.getText())
        postData = url + "&query=" + str(search_term)
        browse_results(name, postData, language, mode)


def browse_home(name, url, language, mode):
    addLog("browse_home: " + url)
    list_videos(url, "home")


def browse_results(name, url, language, mode):
    addLog("browse_results: " + url)
    list_videos(url, "results")


def list_videos(url, pattern):
    video_list = scrape_videos(url, pattern)

    if len(video_list) > 0 and video_list[-1][8] != "":
        next_page_list = scrape_videos(BASE_URL + video_list[-1][8], pattern)
        for next_page_item in next_page_list:
            video_list.append(next_page_item)

    for video_item in video_list:
        if "http" not in video_item[4]:
            image = "https:" + video_item[4]
        else:
            image = video_item[4]
        urldata = (
            video_item[0] + "," + video_item[1] +
            "," + video_item[2] + ",shd," + url
        )
        # addLog('In list_videos before adddir')
        # addLog(video_item)
        addDir(
            video_item[2],
            urldata,
            10,
            image,
            video_item[0],
            video_item[5],
            video_item[6],
            video_item[7],
            isplayable=True,
        )

        if video_item[3] == "uhd":
            urldata = (
                video_item[0]
                + ","
                + video_item[1]
                + ","
                + video_item[2]
                + ",uhd,"
                + url
            )
            addDir(
                video_item[2],
                urldata,
                10,
                image,
                video_item[0],
                video_item[5],
                video_item[6],
                video_item[7],
                isplayable=True,
                isUhd=True
            )

    if len(video_list) > 0 and video_list[-1][8] != "":
        addDir(">>> Next Page >>>", BASE_URL + video_list[-1][8], 11, "")

    xbmcplugin.endOfDirectory(HANDLE)


def scrape_videos(url, pattern):
    html1 = safe_get(url)
    # addLog(html1)
    results = []
    next_page = ""
    if pattern == "home":
        regexstr = (r'name="newrelease_tab".+?img src="(.+?)".+?href="/movie/watch/(.+?)/\?lang=(.+?)"><h2>(.+?)</h2>'
                    r'.+?<div class="info"><p>(.+?)<span>.+?i class=(.+?)</div><div class="stats">(.+?)</div></div> </div></div></div>')
    else:
        regexstr = (r'<div class="block1">.*?href=".*?watch/(.*?)/\?lang=(.*?)".*?<img src="(.+?)".+?<h3>(.+?)</h3>'
                    r'.+?<div class="info"><p>(.*?)<span>.*?i class(.+?)<p class=".*?synopsis">(.+?)</p>(.+?)</a> </div>')
    video_matches = re.findall(regexstr, html1)
    next_matches = re.findall('data-disabled="([^"]*)" href="(.+?)"', html1)
    if len(next_matches) > 0 and next_matches[-1][0] != "true":
        next_page = next_matches[-1][1]
    for item in video_matches:
        # addLog(item)
        movie_name = str(item[3])
        movie_year = item[4]
        movie_def = "shd"
        if "ultrahd" in item[5]:
            movie_def = "uhd"
        if pattern == "home":
            image = item[0]
            movie_id = item[1]
            lang = item[2]
            description = ""
            if "imdb.com" in item[6]:
                imdb_matches = re.findall(r'imdb.com(.+?)title/(.+?)/', item[6])
                imdbId = imdb_matches[0][1]
            else:
                imdbId = ''
        else:
            movie_id = item[0]
            lang = item[1]
            image = item[2]
            try:
                description = html.unescape(item[6])
            except Exception:
                description = ""
            if "imdb.com" in item[7]:
                imdb_matches = re.findall(r'imdb.com(.+?)title/(.+?)/', item[7])
                imdbId = imdb_matches[0][1]
            else:
                imdbId = ''
        results.append(
            (
                str(lang),
                str(movie_id),
                str(movie_name),
                str(movie_def),
                str(image),
                str(description),
                str(imdbId),
                movie_year,
                str(next_page),
            )
        )
    return results


def play_video(name, url, language, mode):
    LOGIN_ENABLED = __settings__.getSetting("login_enabled")
    RETRY_KEY = __settings__.getSetting("retry_key")

    addLog("play_video: " + url)
    addLog("user_login: " + LOGIN_ENABLED)
    addLog("retry_key: " + RETRY_KEY)

    s = requests.Session()

    lang, movieid, moviename, hdtype, refurl = url.split(",")

    if LOGIN_ENABLED == "true":
        get_loggedin_session(s, lang, refurl)

    result = get_video(s, lang, movieid, hdtype, refurl, RETRY_KEY)

    if result is False:
        return False

    xbmcplugin.endOfDirectory(HANDLE)


def get_video(s, language, movieid, hdtype, refererurl, defaultejp="default"):
    video_url = "/movie/watch/%s/?lang=%s" % (movieid, language)

    check_go_premium = "Go Premium"
    check_sorry_message = "SERVERS ARE ALMOST AT CAPACITY"

    headers = {
        "Origin": BASE_URL,
        "Referer": refererurl,
        "User-Agent": USER_AGENT,
    }

    check_premium = s.get(BASE_URL + video_url, headers=headers, cookies=s.cookies, allow_redirects=False)
    if check_premium.status_code in [301, 302, 307, 308]:
        addLog("check_premium: " + str(check_premium.status_code))
        addLog("redirect_location: " + check_premium.headers["location"])
        video_url = "/premium" + video_url

    if hdtype == "uhd":
        video_url = video_url + "&uhd=true"

    addLog("get_video: " + str(video_url))

    html1 = s.get(BASE_URL + video_url, headers=headers, cookies=s.cookies).text

    if re.search(check_go_premium, html1):
        addLog(check_go_premium, "error")
        xbmcgui.Dialog().ok(
            "UltraHD Error - Premium Required",
            "Please add Premium Membership Login details in Addon Settings.",
        )
        return False

    ejp = ""
    if re.search(check_sorry_message, html1):
        addLog(check_sorry_message, "error")
        if defaultejp == "default":
            addLog("no old_ejp", "error")
            xbmcgui.Dialog().yesno(
                "Server Error",
                "Einthusan servers are busy. Please try later or upgrade to Premium account.",
                yeslabel="Retry",
                nolabel="Close",
                autoclose=5000,
            )
            return False
        else:
            addLog("use old_ejp")
            ejp = defaultejp
    else:
        ejp = re.findall(r"data-ejpingables=['\"](.*?)['\"]", html1)[0]
        if ejp == "":
            addLog("no new_ejp", "error")
            xbmcgui.Dialog().yesno(
                "Loading Failed",
                "Please try after some time",
                yeslabel="OK",
                nolabel="Close",
                autoclose=5000,
            )
            return False
        else:
            addLog("found new_ejp")
            __settings__.setSetting("retry_key", ejp)

    addLog("using_ejp: " + ejp)
    jdata = '{"EJOutcomes":"%s","NativeHLS":false}' % ejp
    csrf1 = re.findall(r"data-pageid=['\"](.*?)['\"]", html1)[0]
    # py_2x_3x
    csrf1 = html.unescape(csrf1)
    # csrf1 = HTMLParser.HTMLParser().unescape(csrf1).encode("utf-8")

    postdata = {
        "xEvent": "UIVideoPlayer.PingOutcome",
        "xJson": jdata,
        "arcVersion": "3",
        "appVersion": "59",
        "gorilla.csrf.Token": csrf1,
    }

    rdata = s.post(BASE_URL + "/ajax" + video_url, headers=headers, data=postdata, cookies=s.cookies).text
    ejl = json.loads(rdata)["Data"]["EJLinks"]
    addLog("base64_decodeEInth: " + str(decodeEInth(ejl)))
    url1 = json.loads(base64.b64decode(str(decodeEInth(ejl))))["HLSLink"]
    addLog("url1: " + url1)
    url2 = url1 + ("|%s&Referer=%s&User-Agent=%s" % (BASE_URL, video_url, USER_AGENT))
    addLog("url2: " + url2)
    listitem = xbmcgui.ListItem(name)
    thumbnailImage = xbmc.getInfoImage("ListItem.Thumb")
    listitem.setArt({"icon": "DefaultVideo.png", "thumb": thumbnailImage})
    listitem.setProperty("IsPlayable", "true")
    listitem.setPath(url2)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

    s.close()


def get_loggedin_session(s, language, refererurl):
    LOGIN_USERNAME = __settings__.getSetting("login_username")
    LOGIN_PASSWORD = __settings__.getSetting("login_password")
    addLog("get_loggedin_session: " + refererurl)

    headers = {
        "Origin": BASE_URL,
        "Referer": refererurl,
        "User-Agent": USER_AGENT,
    }

    html1 = s.get(
        BASE_URL + "/login/?lang=" + language,
        headers=headers,
        allow_redirects=False,
    ).text

    csrf1 = re.findall(r"data-pageid=['\"](.*?)['\"]", html1)[0]

    if "&#43;" in csrf1:
        csrf1 = csrf1.replace("&#43;", "+")

    headers["X-Requested-With"] = "XMLHttpRequest"
    headers["Referer"] = BASE_URL + "/login/?lang=" + language

    postdata2 = {
        "xEvent": "Login",
        "xJson": '{"Email":"'
        + LOGIN_USERNAME
        + '","Password":"'
        + LOGIN_PASSWORD
        + '"}',
        "arcVersion": 3,
        "appVersion": 59,
        "tabID": csrf1 + "48",
        "gorilla.csrf.Token": csrf1,
    }

    s.post(
        BASE_URL + "/ajax/login/?lang=" + language,
        headers=headers,
        cookies=s.cookies,
        data=postdata2,
        allow_redirects=False,
    )

    html3 = s.get(
        BASE_URL
        + "/account/?flashmessage=success%3A%3A%3AYou+are+now+logged+in.&lang="
        + language,
        headers=headers,
        cookies=s.cookies,
    ).text

    csrf3 = re.findall(r"data-pageid=['\"](.*?)['\"]", html3)[0]

    postdata4 = {
        "xEvent": "notify",
        "xJson": '{"Alert":"SUCCESS","Heading":"AWESOME!","Line1":"You+are+now+logged+in.","Buttons":[]}',
        "arcVersion": 3,
        "appVersion": 59,
        "tabID": csrf1 + "48",
        "gorilla.csrf.Token": csrf3,
    }

    s.post(
        BASE_URL + "/ajax/account/?lang=" + language,
        headers=headers,
        cookies=s.cookies,
        data=postdata4,
    )

    return s


def decodeEInth(lnk):
    t = 10
    # var t=10,r=e.slice(0,t)+e.slice(e.length-1)+e.slice(t+2,e.length-1)
    r = lnk[0:t] + lnk[-1] + lnk[t + 2 : -1]
    return r


def encodeEInth(lnk):
    t = 10
    # var t=10,r=e.slice(0,t)+e.slice(e.length-1)+e.slice(t+2,e.length-1)
    r = lnk[0:t]+lnk[-1]+lnk[t+2:-1]
    return r


# main starts here
params = get_params()
url = ""
name = ""
mode = 0
language = ""
description = ""

url = urllib.parse.unquote_plus(params.get("url", "")) if params.get("url") else ""
name = urllib.parse.unquote_plus(params.get("name", "")) if params.get("name") else ""
try:
    mode = int(params.get("mode", 0))
except (ValueError, TypeError):
    mode = 0
language = urllib.parse.unquote_plus(params.get("lang", "")) if params.get("lang") else ""
description = urllib.parse.unquote_plus(params.get("description", "")) if params.get("description") else ""

function_map = {}

function_map[0] = select_lang
function_map[1] = select_menu
function_map[2] = select_settings
function_map[3] = browse_home
function_map[4] = menu_alpha
function_map[5] = menu_years
function_map[6] = submenu_decade
function_map[7] = submenu_years
function_map[8] = menu_rating
function_map[9] = menu_search
function_map[10] = play_video
function_map[11] = browse_results
function_map[12] = menu_cast

function_map[mode](name, url, language, mode)
