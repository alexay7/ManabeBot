import requests


MEDIA = ["MANGA", "ANIME"]


async def get_anilist_id(username):
    query = '''
    query ($username: String){
  User(name:$username){
        id
        }
    }
    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'username': username
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    res = requests.post(
        url, json={'query': query, 'variables': variables}).json()

    if "errors" in res:
        print(res)
        return -1
    else:
        return res["data"]["User"]["id"]


async def get_anilist_logs(user_id, page, date):
    query = '''
    query($page:Int, $userId:Int,$date:FuzzyDateInt){
  Page(page:$page,perPage:50){
    pageInfo{
      hasNextPage
      lastPage
      currentPage
    }
    mediaList(userId: $userId,type:ANIME,sort:STARTED_ON,status:COMPLETED,completedAt_lesser:20220201,completedAt_greater:$date) {
      id
      media{
        title {
          romaji
          english
          native
          userPreferred
        },
        format,
        episodes,
        duration
      },
      completedAt {
        year
        month
        day
      },
      startedAt {
        year
        month
        day
      }
      status
  }
  }
}

    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'userId': user_id,
        'page': page,
        'date': date
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    return requests.post(
        url, json={'query': query, 'variables': variables}).json()


async def get_anilist_planning(page, user_id, media,status):
    query = '''
    query($page:Int, $userId:Int,$media:MediaType,$status:MediaListStatus){
    Page(page:$page,perPage:50){
    pageInfo{
      hasNextPage
      lastPage
      currentPage
    }
    mediaList(userId: $userId,type:$media,status:$status) {
      id
      media{
        title {
          romaji
          english
          native
          userPreferred
        },
        meanScore,
        status,
        volumes,
        coverImage {
            large
        },
        episodes,
        siteUrl
      }
  }
  }
}

    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'userId': user_id,
        'page': page,
        'media': media,
        'status':status
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    return requests.post(
        url, json={'query': query, 'variables': variables}).json()


async def get_media_info_by_id(id):
    # Here we define our query as a multi-line string
    query = '''
    query ($id: Int) { # Define which variables will be used in the query (id)
    Media (id: $id, type: MANGA) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
        id
        title {
        native
        }
        volumes
        meanScore
        coverImage{
            large
        }
    }
    }
    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'id': id
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    return requests.post(url, json={'query': query, 'variables': variables})


async def get_media_info(search, media):
    query = '''
        query($query:String, $media:MediaFormat){
        Media(search:$query,format:$media){
        title {
        romaji
        english
        native
        userPreferred
        }
        meanScore
        coverImage{
            extraLarge
        }
        siteUrl
    }
    }
    '''

    variables = {
        'query': search,
        'media': media
    }

    url = 'https://graphql.anilist.co'

    return requests.post(
        url, json={'query': query, 'variables': variables}).json()
