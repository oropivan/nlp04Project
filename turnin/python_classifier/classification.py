'''
Created on Apr 23, 2014
To install scikit
http://scikit-learn.org/stable/install.html

Script that reads JSON files, projects the data, normalizes by the training data and does cross validation 
@author: Ivan Oropeza
'''
from os import listdir, makedirs, remove
from os.path import isfile, splitext, basename, isdir
from sklearn import svm 
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.cluster import KMeans
from numpy.linalg import norm
from numpy import dot
import json
import numpy as np
import sys
import math
import random

def traverseAndWrite(root, output_dir, data_size, data_set, use_audio_features, use_lyric_features):
    if not isfile(root):
        parent = basename(root)
        for f in listdir(root):
            if len(data_set.get(parent,[])) == data_size:
                return
            traverseAndWrite(root +"/"+ f,output_dir, data_size, data_set, use_audio_features, use_lyric_features)
    else: 
        fileName, fileExtension = splitext(root)
        jsonFile = ''.join([fileName, ".json"])
        lyricFile = ''.join([fileName, ".txt"])
#         if not isfile(jsonFile) or not isfile(lyricFile):
#             return
        audioFeatures = []
        lyricFeatures = []    
        try:
            json_data=open(jsonFile)
            data = json.load(json_data)
            json_data.close()
        except (ValueError, IOError):
            f = open(output_dir,'a+')
            f.write(jsonFile)
            f.write('\n')
            f.close()
            try:
                remove(jsonFile)
                remove(lyricFile)
            except OSError:
                print 
            return
        genre = str(data['genre'])
        if use_audio_features:    
            timbre = data['segments_timbre']
            array = np.array(timbre)
            mean = np.mean(array, axis=0).tolist()
            std = np.std(array, axis=0).tolist()
            audioFeatures = mean + std
            
            pitches = data['segments_pitches']
            array = np.array(pitches)
            mean = np.mean(array, axis=0).tolist()
            std = np.std(array, axis=0).tolist()
            audioFeatures = audioFeatures + mean + std
        if use_lyric_features:    
            lyricFeatures = data.get('lang_vector',[])
            
        featureVector = audioFeatures + lyricFeatures
        if not data_set.get(genre,[]):
            data_set[genre]=[]
        if len(data_set[genre]) < data_size:
            data_set[genre].append(featureVector)
            
            
def splitData (data_set, partition_index, cross_validation):
    training_set = []
    testing_set = []
    start_index = partition_index*len(data_set[0])/cross_validation
    end_index = (partition_index+1)*len(data_set[0])/cross_validation
    for key in data_set.keys():
        for i in range(start_index):
            training_set.append((key,data_set[key][i]))
        for i in range(start_index, end_index):
            testing_set.append((key,data_set[key][i]))
        for i in range(end_index, len(data_set[0])):
            training_set.append((key,data_set[key][i]))       
    return training_set, testing_set

def normalize(training, testing):
    array = np.array(training)
    std = np.std(array, axis=0)
    normal_array = array/std    
    ntraining = normal_array.tolist()
    
    array = np.array(testing)
    normal_array = array/std    
    ntesting = normal_array.tolist()
    return ntraining, ntesting
    
def prettyPrint(array, num_map, genre_map):
    print ''.join(['{:<11}'.format('')]+['{:<11}'.format(genre) for genre in sorted(genre_map.keys())])
    print '\n'.join(['{:<11}'.format(num_map[index]) + ''.join(['{:<11}'.format(round(item,2)) for item in row]) 
      for index,row in enumerate(array)])

def prettyPrintCSV(array, num_map, genre_map):
    return ','.join(['{:<11}'.format('')]+['{:<11}'.format(genre) for genre in sorted(genre_map.keys())]) +'\n' + '\n'.join(['{:<11}'.format(num_map[index]) +","+ ','.join(['{:<11}'.format(round(item,2)) for item in row]) 
      for index,row in enumerate(array)])
def angle_between(a,b):
  arccosInput = dot(a,b)/norm(a)/norm(b)
  arccosInput = 1.0 if arccosInput > 1.0 else arccosInput
  arccosInput = -1.0 if arccosInput < -1.0 else arccosInput
  return math.acos(arccosInput)

def aggregateResults(scores, genre_map):
    aggregated_results = {genre_map[key]:{genre_map[key2]:0.0 for key2 in sorted(genre_map.keys())} for key in sorted(genre_map.keys())}
    for result in scores:
        for classification in result.keys():
            for label in result[classification]:
                aggregated_results[classification][label] +=1
    # Warning TO BE transposed before returning
    confusion_matrix = [ [aggregated_results[classification][label] for label in sorted(aggregated_results[classification].keys())] for classification in sorted(aggregated_results.keys())]
    array = np.array(confusion_matrix)
    total = np.sum(array, axis=1)
    percentages = array/total
    
    percentages = np.transpose(percentages)
    array = np.transpose(array)
    return array.tolist(), percentages.tolist()
    
def evaluate_classifier(clf, Y, X, genre_map):
    results = {genre_map[key]:[] for key in genre_map.keys()}
    for i in range(len(Y)):
        results[Y[i]].append(clf.predict(X[i])[0])
    return results

def main (argv):
    if not len(argv) == 7:
        print "Insufficient parameters"
        print "<dataPath> <output_dir> <data_size> <cross_validation> <use_audio_features> <use_lyric_features>"
        sys.exit()
    dataPath, output_dir, data_size, cross_validation, use_audio_features, use_lyric_features = argv[1:] 
    use_audio_features = use_audio_features in ['true', 'True']
    use_lyric_features = use_lyric_features in ['true', 'True']
    data_size = int(data_size)
    cross_validation = int(cross_validation)
    if not isdir(output_dir):
        makedirs(output_dir)
    data_set = {}
    traverseAndWrite(dataPath, output_dir+"errorFiles", data_size, data_set, use_audio_features, use_lyric_features)
    
    # mapping functions
    genre_map={}
    num_map={}
    mapping = 0
    for key in sorted(data_set.keys()):
        genre_map[key] = mapping
        num_map[mapping] = key
        mapping +=1
    # use genre mapping to int for dataset classes
    tmp = {}
    for key in sorted(data_set.keys()):
        tmp[genre_map[key]] = data_set[key]
    data_set = tmp
    
    #shuffle the list
    for key in (data_set.keys()):
        random.shuffle(data_set[key])
    
    # name_classifier
    # YOU ONLY NEED TO ADD/MODIFY THE CLASSIFIERS HERE
    name_classifier = []
    name_classifier.append(('poly_kernel_svm',svm.SVC(kernel='poly')))
    name_classifier.append(('rbf_kernel_svm',svm.SVC(kernel='rbf')))
    name_classifier.append(('linear_svm',svm.LinearSVC()))
    name_classifier.append(('3_KNN',KNeighborsClassifier(n_neighbors=3)))
    name_classifier.append(('1_KNN',KNeighborsClassifier(n_neighbors=1)))
    name_classifier.append(('tree',DecisionTreeClassifier(random_state=0)))
    ##################################################
    ######
    #CLUSTER TRANSFORM HERE
        
    kmeans = KMeans(4)
    kmeans_data = [ data_point for key, value in data_set.iteritems() for data_point in value ]
    kmeans.fit(kmeans_data)
    clusters = kmeans.cluster_centers_
    tmp ={}
    for key in data_set.keys():
        tmp[key] = []
        for data_point in data_set[key]:
            projection = []
            for cluster in clusters:
                a = np.array(data_point)
                projection.append(norm(a-cluster))
                projection.append(angle_between(a,cluster))
            tmp[key].append(projection) 
    data_set = tmp
    ######
    #cross validation
    name_classifier_scores = {t:[] for t in name_classifier}
    for i in range(cross_validation):
        # partition data for testing and training
        training_set, testing_set = splitData(data_set, i, cross_validation)
        
        #normalize training data        
        Y_train = [x[0] for x in training_set]
        Y_test = [x[0] for x in testing_set]
        
        X_train = [x[1] for x in training_set]
        X_test = [x[1] for x in testing_set]
        
        X_train, X_test = normalize(X_train, X_test)
        
        # use classifiers
        for t in name_classifier:
            clf = t[1]
            clf.fit(X_train, Y_train) #feed training data_set
            results = evaluate_classifier(clf, Y_test, X_test, genre_map)
            name_classifier_scores[t].append(results)
            
    # Print the output information
    for t in name_classifier_scores.keys():
        clf = t[1]
        output_file =output_dir + t[0] + '.csv'
        scores = name_classifier_scores[t]
        f = open(output_file,'w')
        confusion_matrix_values,confusion_matrix_percentages = aggregateResults(scores,genre_map)
        f.write('Values Prediction\True Class')
        f.write(prettyPrintCSV(confusion_matrix_values, num_map, genre_map))
        f.write('\n')
        f.write('Percentages Prediction\True Class')
        f.write(prettyPrintCSV(confusion_matrix_percentages, num_map, genre_map))
        f.close()


if __name__ == "__main__":
    main(sys.argv)