from datetime import datetime
import networkx as nx
import string
import json
import sys
import logging

HEAD = -1
LAST = 0
FIRST = 0
MAX_SECONDS = 59

class Tweet(object):
    """
    Represents a tweet.
    Holds the tweet Datetime and all combinations of hashtag edges.
    For debugging purpose the tweet number, which represents the nth tweet
     created.
    Tweet instances will be placed in the AverageDegree.tweetList list. the
     newest tweet will be appended to the AverageDegree.tweetList. The oldest
     tweet is the first location within the list. When tweets are older than
     60 seconds they will be removed from the AverageDegree.tweetList. The
     hashtagEdgeList is used to create and edges from the tweet hashtag graph.
    """
    def __init__(self, tweetTime ,builtEdgeList, tweetNumber):    
        self.hashtagEdgeList = list(builtEdgeList)
        self.createdDatetime = tweetTime
        self.tweetNumber = tweetNumber
    
class AverageDegree(object):
    """
    This class is the main class for parsing tweets for hashtags and
     calculating the average degree of a tweet hashtag graph. networkx
     is used for creating the tweet hashtag graph.
    The overall flow of the application is listed below.

    1. Open input and output files.
    2. Get json line
    3. Check if json line has 'created_at' and 'hashtags'
    4. Extract 'create_at' and 'hashtags'
    5. Add new edges
    6. Calculate tweet time difference 
    7. Remove hashtag edges that are over 60s old
    8. Remove nodes that have no edges
    9. Calculate edge average
    """
    def __init__(self, inFileName, outFileName):
        """
        Initialize member variables
        """
        self.hashtagGraph = nx.Graph()
        self.tweetList = []
        self.builtEdgeList = []
        self.inFileName = inFileName
        self.outFileName = outFileName
        self.inFile = None
        self.outFile = None
        self.replaceCharsWithWhiteSpace = string.whitespace
        self.table = string.maketrans(self.replaceCharsWithWhiteSpace, " "*len(self.replaceCharsWithWhiteSpace))
        self.writeBufferList = []

    def setupLogging(self, logLevel):
        self.logLevel = logLevel
        fmt = '%Y-%m-%d_%H%M'
        logStartTime = datetime.now().strftime(fmt)
        logging.basicConfig(filename = "./tweet_output_2015/log_{}.log".format(logStartTime),
                            format = '%(asctime)s:%(module)s:%(message)s',
                            filemode = 'w', 
                            level= logLevel)
        logging.debug("DEBUG LOG TEST")

    def openFiles(self):
        """
        Open files
        """
        self.inFile = open(self.inFileName, 'r')
        self.outFile = open(self.outFileName, 'w')
        
    def closeFiles(self):
        """
        Close files
        """
        self.inFile.close()
        self.outFile.close()
        
    def buildEdgeList(self, hashtagsList):
        """
        Generate all edge combinations from the hashtags that are contained
         within hashtagsList. This method is recursive.
        """
        hashtagLen = len(hashtagsList)
        if hashtagLen > 1:
            for index in range(1, hashtagLen):
                self.builtEdgeList.append((hashtagsList[FIRST], hashtagsList[index]))
            hashtagsList.pop(FIRST)
            self.buildEdgeList(hashtagsList)
        
    def createTweetDateTime(self, dateTimeString):
        """
        Converts the string tweet datetime to a datetime type.
        """
        tweetDatetime = datetime.strptime(dateTimeString, "%a %b %d %H:%M:%S +0000 %Y")
        return tweetDatetime
    

    def removeTimedOutTweets(self):
        """
        This method copies all the objects that need to be removed
         in a separate list. That list is iterated to remove
         the tweet objects from tweetList as well as all edges
         of the tweet.
        """
        removeTweetList = []
        headTime = self.tweetList[HEAD].createdDatetime
        for index, tweet in enumerate(self.tweetList):
            tweetDiffTime = headTime - tweet.createdDatetime
            tweetDiffTime = int(tweetDiffTime.total_seconds())
            if (tweetDiffTime > MAX_SECONDS):
                removeTweetList.append(tweet)
            else:
                break

        for rmTweet in removeTweetList:
            self.hashtagGraph.remove_edges_from(rmTweet.hashtagEdgeList)
            self.tweetList.remove(rmTweet)
        
        self.removeZeroDegreeNodes()


    def debugRemovedTweets(self):
        for xTweet in self.tweetList:
            logging.debug(xTweet.createdDatetime)
        logging.debug('---')
    
    def removeZeroDegreeNodes(self):
        """
        When a hashtag edges are removed some nodes may no longer have any
         edges. This method will remove these nodes from the graph.
        """
        nodesToRemove = []
        for node in self.hashtagGraph.nodes_iter():    
            if (self.hashtagGraph.degree(node) == 0):
                nodesToRemove.append(node)
        if (len(nodesToRemove) > 0):
            self.hashtagGraph.remove_nodes_from(nodesToRemove)
        
    def addTweetHashtagEdges(self):
        """
        This method will add the edges that are within the builtEdgeList list.
        If an edge includes a node that is not in the graph, Netwrokx will
         automatically add those nodes.
        """
        self.hashtagGraph.add_edges_from(self.builtEdgeList)
    

    def calculateAndWriteAverageDegree(self):
        """
        Calculates the average degree and writes it to the output file.
        """
        #logging.debug(nx.degree(self.hashtagGraph))
        if (self.hashtagGraph.number_of_nodes() == 0):
            self.writeBufferList.append(0)
        else:
            averageDegree = (float( sum(nx.degree(self.hashtagGraph).itervalues()) )/
                            self.hashtagGraph.number_of_nodes())
            self.writeBufferList.append(averageDegree)


    def run(self):
        #Set logging
        #self.setupLogging(logging.DEBUG)
        #self.setupLogging(logging.INFO)

        #Open input files
        self.openFiles()

        wrInnerCnt = 0
        wrOutterCnt = 0
        #Remove dots for better performance
        wb = self.writeBufferList
        wr = self.outFile.write
        tweetListAppend = self.tweetList.append
        
        #Iterate of each line
        for index, line in enumerate(self.inFile):
            #logging.debug(index)
            jsonData = json.loads(line)
            
            #Check if it is line is a tweet
            if ('created_at' in jsonData and 'entities' in jsonData):
                tweetHashtagsLen = len(jsonData['entities']['hashtags'])
                
                if (tweetHashtagsLen > 1):
                    tweetHashtagSet = set()
                    del self.builtEdgeList[:]
                    for hashtagEntity in jsonData['entities']['hashtags']:
                        tweetHashtagSet.add(hashtagEntity['text'])

                    #Create hashtagEdgeList and add hashtag edges
                    if (len(tweetHashtagSet) > 1):
                        del self.builtEdgeList[:]
                        self.buildEdgeList(list(tweetHashtagSet))
                        self.addTweetHashtagEdges()
                    
                #Calculate tweetTime    
                tweetDateTime = self.createTweetDateTime(jsonData['created_at'])
                
                #Create tweet (no hashtage or single hashtag will be stored for time window)
                tweet = Tweet(tweetDateTime, self.builtEdgeList, index)
                
                #Add tweet to tweetList
                tweetListAppend(tweet)
                self.tweetList.sort(key=lambda x: x.createdDatetime)
                
                #Remove tweets that timed out
                self.removeTimedOutTweets() #Contains tweetListIndex
                #self.debugRemovedTweets()

                #Calculate and write average degree
                self.calculateAndWriteAverageDegree()
                
                #Write to output file every 1K loops 
                if index % 1000 == 999:
                    map(lambda x:wr("{:.2f}\n".format(x)), wb)
                    del wb[:]
                    wrInnerCnt +=1
                    
        #Write to file all remaining average degrees
        map(lambda x:wr("{:.2f}\n".format(x)), wb)
        self.closeFiles()
        


if __name__ == '__main__':

    ad = AverageDegree(sys.argv[1], sys.argv[2])
    ad.run()
  
    