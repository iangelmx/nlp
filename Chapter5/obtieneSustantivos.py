#-*- coding: utf-8 -*-
import nltk
import re
from collections import defaultdict
from nltk.corpus import brown
from pickle import dump
from pickle import load
from functionsNLP import *
from mariamysqlib import *

def lemmatizerBD(rutaArchivoLemmas, tokens, tabla, saveToTable=False): #Tabla es a donde se grabarán los tokens y a donde se lemmatizará
	if saveToTable == True:
		grabaEnBD(tabla, tokens, update=False)
	recoverFromDB = doQuery("SELECT token FROM "+tabla+" ORDER BY id;")
	if recoverFromDB:
		tokens=[]
		for elemento in recoverFromDB:
			tokens.append(elemento[0])
	lemmas = open(rutaArchivoLemmas, mode="r", encoding="utf-8")
	cadena=lemmas.readline()
	conteo=0
	transaccion="START TRANSACTION;\n"
	while cadena != '':
		try:
			[lemma, palabra]=cadena.split('\n')[0].split('\t')
			if palabra in tokens:
				transaccion+="UPDATE "+tabla+" set token='"+str(lemma)+"' WHERE token='"+str(palabra)+"';"
				#print("UPDATE tokens_lemmas set token='"+str(lemma)+"' WHERE token='"+str(palabra)+"';")
			if conteo % 1000 == 0:
				print("Actualizando Tokens Conteo-> "+str(conteo))
			cadena=lemmas.readline()
			conteo+=1
		except Exception as ex:
			print(ex)
			pass
	transaccion+="COMMIT;"
	doQuery(transaccion)
	print("Terminó lemmatizing")
	recoverFromDB = doQuery("SELECT token FROM "+tabla+" ORDER BY id;")
	if recoverFromDB:
		tokensSinLemas=[]
		for elemento in recoverFromDB:
			tokensSinLemas.append(elemento[0])
	return tokensSinLemas

def lemmatizerBD2(rutaArchivoLemmas, tabla):
	recoverFromDB = doQuery("SELECT token FROM "+tabla+" ORDER BY idToken;")
	if recoverFromDB:
		tokens=[]
		for elemento in recoverFromDB:
			tokens.append(elemento[0])
	lemmas = open(rutaArchivoLemmas, mode="r")#, encoding="utf-8")
	transaccion = []
	transaccion.append("START TRANSACTION;")
	cadena=lemmas.readline()
	conteo=0
	while cadena != '':
		try:
			cadena = cadena.split(' ')
			forma = cadena[0]
			lemma = cadena[len(cadena)-2]
			forma = forma.replace('#', '')
			#print("Forma lema-> "+forma+" "+lemma)
			if forma in tokens:
				transaccion.append("UPDATE "+tabla+" SET lemmaToken='"+lemma+"' WHERE token ='"+forma+"'")
			if conteo % 100000 == 0:
				print("Actualizando Tokens Conteo-> "+str(conteo))
			cadena=lemmas.readline()
			conteo+=1
		except Exception as ex:
			input(ex)
			pass
	transaccion.append("COMMIT;")
	return doTransaction(transaccion)


""" 
Ejercicio:
Entrenar un etiquetador de NLTK nltk.UnigramTagger con oraciones de cess_esp
Oración 10 del archivo e960401 
"""
[tokens, rawText] = getTextTokens("e960401_txt.txt", backTextString=True)

listaOraciones = separaPorOraciones(rawText)
existe=False
unigramEspTagger=None
try:
	entrada = open('espTagger.pkl', 'rb')
	unigramEspTagger = load(entrada)
	entrada.close()
	existe=True
except Exception as ex:
	print(ex)

if unigramEspTagger == None or existe==False:
	print("Generará el archivo")
	patterns = [
	    (r'.*o$', 'NCMS'),               # Sustantivo Masculino
	    (r'.*a$', 'NCFS'),          		 # Sustantivo Femenino
	    (r'.*as$', 'NCFP'),
	    (r'.*os$', 'NCMP')
	]
	regexp_tagger = nltk.RegexpTagger(patterns)
	cess_tagged_sents = nltk.corpus.cess_esp.tagged_sents()

	oracion = listaOraciones[10]
	oracionTokenizada = nltk.Text(nltk.word_tokenize(oracion))

	var = regexp_tagger.tag( oracionTokenizada )

	""" Training nltk.UnigramTagger usando oraciones desde cess_esp """
	unigramEspTagger = nltk.UnigramTagger( cess_tagged_sents, backoff=nltk.RegexpTagger(patterns))

	archivoTagger = open('espTagger.pkl', 'wb')
	dump(unigramEspTagger, archivoTagger, -1)
	archivoTagger.close()

print("Etiquetará del archivo pkl")

listaSustantivos = []

transaccion = []
transaccion.append("START TRANSACTION;")
transaccion.append("TRUNCATE sustantivosLematizados;")

for enunciado in listaOraciones:
	oracionTokenizada=nltk.Text(nltk.word_tokenize(enunciado))
	example = unigramEspTagger.tag(oracionTokenizada)
	for item in example:
		listaItem = list(item)
		#print( "item: -> "+str(listaItem) )
		try:
			if listaItem[1][0] == 'n' or listaItem[1][0] == 'N':
				#input("Es sustantivo-> "+str(listaItem))
				listaSustantivos.append(listaItem[0])
		except Exception as ex:
			pass
			#print(ex)
			#print("Error... No está mapeada la palabra: "+str(listaItem[0]))

listaSustantivos=set(listaSustantivos)

for sustantivo in listaSustantivos:
	transaccion.append('INSERT INTO sustantivosLematizados(token) VALUES("'+sustantivo+'");')
transaccion.append("COMMIT;")

resultT=doTransaction(transaccion)

print(resultT)

a=lemmatizerBD2("generate.txt", "sustantivosLematizados")

print(a)




"""print(unigram_tagger.evaluate(train_sents))"""

##print(regexp_tagger.tag( nltk.Text(nltk.word_tokenize(train_sents)) ))

"""
Extraer todos los sustantivos de e960401, lematizarlos y aplicar set()
Si empieza con n, se obtiene la palabra.
"""