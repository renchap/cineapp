import json, urllib2,sys, time, urllib, os, time
from cineapp import app,db
from cineapp.models import Movie

def download_poster(movie):

	""" Function that downloads the poster from the tvmdb and update the database with the correct path
	"""
	try:
		img = urllib2.urlopen(movie.poster_path)
		localFile = open(os.path.join(app.config['POSTERS_PATH'], os.path.basename(movie.poster_path)), 'wb')
		localFile.write(img.read())
		localFile.close()

	except Exception as e:
		print e
		return False

	# Let's update the field in the database
	movie.poster_path=os.path.basename(movie.poster_path)
	try:
		db.session.commit()
	except:
		return False

	# If we are here, everything is okay
	return True

def search_movies(query):
	"""
		Function that query tvmdb.org and return a list of movies
	"""
	# Local variables
	languages_list=["fr"]
	complete_list=[]

	# Query the API using the query in parameter
	for cur_language in languages_list:
		data = urllib2.urlopen(os.path.join(app.config['API_URL'],("search/movie?api_key=" + app.config['API_KEY'] + "&language=" + cur_language + "&query=" + urllib.quote(query.encode('utf-8')))))

		# Put the result into a dictionnary
		result=json.load(data)

		# We can have more than one page containing result 
		# Fetch the total_pages number and browse each page
		for cur_page in range(1,int(result["total_pages"])+1,1):
			data = urllib2.urlopen(os.path.join(app.config['API_URL'],("search/movie?api_key=" + app.config['API_KEY'] + "&language=" + cur_language + "&query=" + urllib.quote(query.encode('utf-8')))) + "&page=" + str(cur_page))

			# Put the results of the current page into a dictionnary
			movies_list=json.load(data)

			for cur_movie in movies_list['results']:
				complete_list.append(cur_movie)

	return complete_list

def get_movie(id):
	"""
		Function that fill a movie object using TVMDB database
	"""
	# Fetch global configuration parameters
	config_api=json.load(urllib2.urlopen(os.path.join(app.config['API_URL'], "configuration?api_key=" + app.config['API_KEY'] +"&language=fr")))
	base_url=config_api['images']['secure_base_url']
	
	# Fetch the movie data
	movie=json.load(urllib2.urlopen(os.path.join(app.config['API_URL'],("movie/" + str(id) + "?api_key=" + app.config['API_KEY'] + "&append_to_response=credits,details&language=fr"))))

	# Fetch the director form the casting
	director=None
	for cur_guy in movie['credits']['crew']:
		if cur_guy['job'] == "Director":
			director=cur_guy["name"]
			break

	# Try to get the poster in French	
	movie_poster=json.load(urllib2.urlopen(os.path.join(app.config['API_URL'],("movie/" + str(id) + "/images?api_key=" + app.config['API_KEY'] + "&language=fr&include_image_language=fr,null"))))

	# Fetch poster url !
	url = None
	try:
		url = base_url + 'w185' + movie_poster['posters'][0]['file_path']
	except IndexError:

		# No poster with the french or null language= => Fallback in english
		movie_poster=json.load(urllib2.urlopen(os.path.join(app.config['API_URL'],("movie/" + str(id) + "/images?api_key=" + app.config['API_KEY']))))

		try:
			url = base_url + 'w185' + movie_poster['posters'][0]['file_path']
		except IndexError:
			pass

	# Create the movie object
	movie_obj=Movie(name=movie['title'],
		release_date=movie['release_date'],
		url="http://www.themoviedb.org/movie/" + str(id),
		tmvdb_id=id,
		poster_path=url,
		director=director
	)

	return movie_obj

if __name__ == "__main__":
	test=search_movies("tuche")
	for cur_test in test:
		print cur_test

	movie=get_movie(550)
	print movie.name
	print movie.director
	print movie.release_date
	print movie.poster_path
	
