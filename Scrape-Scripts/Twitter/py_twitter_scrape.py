#!/usr/bin/env python
# -*- coding: utf-8 -*-:

__author__="Esaie Kuitche"
__date__ ="$2018-02-016 09:15:14$"
__version__ = '0.1'

"""
`` **module description**:
This module counts the number of times a given URL is shared on social media and
 add this information in a mongodb
required modules:
	-socialshares
	-tweepy
	-json
Command line: python get_share_count_for_articles.py
"""

from pymongo import MongoClient, DESCENDING
import json
import socialshares
import time
import tweepy
import urllib3
import urllib
urllib3.disable_warnings()
urllib.request.getproxies = lambda: {} 

proxies = {'http': 
'http://oci-ifo:85KNqo1dBVGb@us-il.proxymesh.com:31280', 'https': 
'http://oci-ifo:85KNqo1dBVGb@us-il.proxymesh.com:31280'}



def connection_to_mongo():
	"""
	Cette fonction a pour role de:
	1- se connecter à mongodb (il y a deux scénarios possible : avec ou sans mot
	 de passe)
	2- spécifier la base de données sur laquelle on souhaite travailler
	:return: Cette fonction retourne la collection articles qui sera utilisée 
	plus tard.
	"""

	#uri = "mongodb://oci_user:oci_pass_2018%@206.167.88.72:27017/scrapy"
	
	uri = "mongodb://127.0.0.1:27017/scrapy"
	client = MongoClient(uri)
	db = client['scrapy']    
	collection = db.articles

	return collection


def get_articles_from_mongo(n, collection):
	"""
	Cette fonction effectue une rêquette pour selectionner n (par défaut n = 100
	) articles récents qui n'ont pas le
	champs shares
	:param n
	nombre d'article à selectionner
	:param collection:
	collection est un pointeur sur la collection article
	:return:
	cette fonction retourne un dictionnaire ayant pour clés les IDs des n articl
	es et pour valeur un dictionnaire dont
	les clés sont  les noms des réseaux sociaux dans lequel les valeurs sont 
	initialisées à 0
	Par exemple : data = {id1: {"facebook":0, "google": 0, "linkedin":0, 
	"pinterest":0, "twitter":0, "reddit" : 0}, ...}
	"""

	articles = collection.find({ "shares": { "$exists": 0, "$ne": 1 } }, 
	           {"redirected_article_url":1}).sort("_id", DESCENDING).limit(100)
	
	datas = dict()
	for x in articles:
		id = x["_id"]
		url = x['redirected_article_url']

		if url.count("temp_url-")>0:
			url = url.split("temp_url-")[1]

		url = url.strip()

		datas[id] = {"url": url, "facebook":0, "google": 0, "linkedin":0, 
		             "pinterest":0, "twitter":0, "reddit" : 0}

	return datas

def limit_handled(cursor):
	while True:
		try:
		    yield cursor.next()
		except tweepy.RateLimitError:
		    print ("pause")
		    time.sleep(15 * 60)
		except tweepy.TweepError:
			print ("Error pause")
			time.sleep(15 * 60)

def count_number_of_sharing(datas, collection, api):
	"""
	Cette fonction utilise deux librairies pytthons :
	1- la premiere socialShares permet de compter le nombre de share sur  
	"facebook", "linkedin", "pinterest" et "reddit"
	2- la seconde tweepy permet de faire une requette searh sur Twitter en 
	passant l'url et puis effectue un count sur
	la liste retournée (Qui est une approximation du nombre de share de l'URL)
	:param datas:
	datas est le dictionnaire retourné par getArticlesFromMongo, il d'agit d'un
	 dictionnaire ayant pour clés les IDs des
	 n articles et pour valeur un dictionnaire dont les clés sont  les noms des 
	 réseaux sociaux dans lequel les valeurs
	 ont initialisées à 0Par exemple : data = {id1: {"facebook":0, "google": 0,
	  "linkedin":0, "pinterest":0,
	 "twitter":0, "reddit" : 0}, ...}

	:param collection:
	collection est un pointeur sur la collection article
	:param api:
	api est un pointeur qui nous permet d'utiliser la requette search sur twitter
	:return:
	cette fonction
	"""
	for id, data in datas.items():
		flag = False
		while flag == False:
					
			counts = socialshares.fetch(data['url'], ['facebook', 'pinterest', 
				                                      'google', 'linkedin', 'reddit'])

			try:		
				data["facebook"] = int(counts['facebook']['share_count'])
			except:
				flag = True
				data["facebook"] = -1


			try:			
				data["google"] = int(counts['google'])
			except:
				flag = True			
				data["google"] = -1

			try:
				data["linkedin"] = int(counts['linkedin'])
			except:
				flag = True			
				data["linkedin"] = -1

			try:
				data["pinterest"] = int(counts['pinterest'])
			except:
				flag = True			
				data["pinterest"] = -1

			try:
				data["reddit"] = int(counts['reddit']['ups'] + counts['reddit']['downs'])
			except:
				#flag = True			
				data["reddit"] = 0
			
			try:
				"""
				public_tweets = api.search(q = data["url"], count = 1000, rpp = 1)
				count =  len(public_tweets)
				data["twitter"] = int(count)
				"""					
				count = 0
				for public_tweets in limit_handled(tweepy.Cursor(api.search, q=data["url"], count = 100).items()):		
					count +=  1
				data["twitter"] = int(count)					
				
				
			except:
				flag = True			
				data["twitter"] = -1
			
			print (data)
			if	flag == True:		
				time.sleep(900)
				flag = False
			else:
				flag = True
				
		data.pop("url")
		collection.update({"_id" : id },{"$set" : {"shares": data}})				
		print (data)


def main():
	"""
	Cette fonction se connecte à base de données scrapy, sectionne les n plus 
	récents articles qui n'ont pas l'attribut
	 shareCount, effectue les reqettres necessaire pour obtenir le shareCount 
	 sur les réseaux sociaux et l'ajoute comme
	 nouveau attribut à chaque l'objet concerné.
	:return:
	Cette fonction met à jour les n articles selectionnés en ajoutant leur 
	shareCount.
	"""
	consumer_key = "tYveQYnFeVZia4wXdXNGTs8dV"
	consumer_secret = "nYpv4tZpFEKPTWsZZCbrevoDs6y0nj3uEgBQaRSSDeoJSpq84x"
	access_token = "556851934-ZFvvc8qArVJi29qBgjKd1qEvZAH8Nx069WWpOsDz"
	access_token_secret = "1QJUnXFpeeH932gVvzldj1yWiU3NK4q5XxBkK7dNbgWo7"
	auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
	auth.set_access_token(access_token, access_token_secret)
	api = tweepy.API(auth)
	n = 100
	collection = connection_to_mongo()
	datas = get_articles_from_mongo(n, collection)
	count_number_of_sharing(datas, collection, api)


if __name__ == "__main__":
	"""
	Cette fonction appelle la fonction main et marque une pause de 60 seconde 
	soit 1 min.
	"""
	while True:
		main()
		time.sleep(60)
