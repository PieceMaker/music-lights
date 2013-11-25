freqbins <- function(filename) {

  results <- read.csv(filename, header = T, stringsAsFactors = F)

  #The last column seems to be all NAs. Thus, remove it from the data frame.
  results <- results[,-ncol(results)]
  #Remove 0 frequency columns. This will need to be changed whenever the final naming convention is added.
  #tempdf[,-which(names(results) %in% c('Left.0.0.Hz', 'Right.0.0.Hz'))]
  results <- results[(rowSums(results) > 0),]
  results.colmeans.loudness <- as.numeric(colMeans(results))

  results.mat <- as.matrix(results)

  #Normalize each row so that they individually sum to 1.
  mat.norm <- results.mat/rowSums(results.mat)
  results <- as.data.frame(mat.norm)
  rm(results.mat)
  rm(mat.norm)

  results.colmeans.std <- as.numeric(colMeans(results))

  #Prob represents a loudness-weighted probability
  bins.df <- data.frame(Start = 0, End = 0, Prob = 0, StartCol = 0, EndCol = 0)

  i = 1
  while(i <= 1000) {
  
    startbin <- i
  
    binsum <- 0
  
    while((binsum < 1/32) & (i <= 1000)) {
      
      binsum <- binsum+results.colmeans.std[i]
      
      endbin <- i
      
      i = i+1
      
    }
  
    bins.df <- rbind(bins.df, data.frame(Start = as.numeric(gsub('\\bX([0-9.]+)\\b\\.Hz', '\\1', names(results[max(startbin, 1)]))),
                                         End = as.numeric(gsub('\\bX([0-9.]+)\\b\\.Hz', '\\1', names(results[min(endbin, ncol(results))]))),
                                         Prob = binsum,
                                         StartCol = startbin,
                                         EndCol = endbin))
  
  }

  bins.df <- bins.df[-1,]
  
  avgloudness <- c()
  
  for(j in 1:nrow(bins.df)) {
    
    #Get the j'th row of bins.df
    bin <- bins.df[j,]
    
    avgloudness[j] <- mean(results.colmeans.loudness[bin$StartCol:bin$EndCol])
    
  }
  
  bins.df$AvgLoudness <- avgloudness
  
  return(bins.df)
  
}