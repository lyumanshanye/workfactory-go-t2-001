#######  This is a package that includes many useful functions #######
# Just source this function and then you are able to use it.
# By Wenhao Li, liwenhao@marshall.usc.edu, www.wenhao-li.com

# # === Set path ===
# currentPath = dirname(rstudioapi::getActiveDocumentContext()$path)
# setwd(currentPath) # set the path of this R file as the current path

# == Load Packages ==
package_names = c("data.table", "ggplot2", "readxl", "writexl", "R.matlab",  "sandwich",  "lmtest",
                  "scam", "stargazer","roll", "car",  "reshape2", "forecast", "nleqslv",  "latex2exp", 
                  "zoo", "plyr", "tsoutliers", "pracma", "vars", "tseries", "fda", "lubridate", 
                  "stringr",  "margins", "readstata13", "rmatio", "openxlsx" ) 
for(iter in 1:length(package_names)){
  if (!require(package_names[iter], character.only = TRUE)) {  # If not already installed the packages
    install.packages(package_names[iter], dependencies = TRUE)
  }
  library(package_names[iter],character.only = TRUE)  # Then include the required package
}

# === Process year month date format of "2008m10" ===
process_yearmon<- function(x){
  Year = as.numeric(substr(x,1,4))
  Month=as.numeric(substr(x,6,7))
  YearMon=as.yearmon(Year+(Month-1)/12)
  return( as.Date(YearMon) )
}

# === average and sum function that deal with NAs ===
mean_fun <- function( x ){
  return( mean(x, na.rm=TRUE) )
}
sum_fun <- function( x ){
  return( sum(x, na.rm=TRUE) )
}

# === Generate Differences ======
GenDiff <- function( variable, Lag=1 ){
  index = 1:(length(variable)-abs(Lag))
  if(Lag>0){
    return(  c( variable[index+Lag] - variable[index],  rep(NA,Lag))  )
  }else{
    Lag = -Lag
    return(  c(rep(NA,Lag), variable[index+Lag] - variable[index])  )
  }
}
GenLogDiff <- function( variable, Lag=1 ){  # Diff negative means shifting forward.
  return(GenDiff(log(variable),Lag))
}
# ==== Gen Lagged Variables ======
Lag_fun <- function(x, lag=1){  
  # The default is the lag of variables. If lag<0, then it becomes the forward of variables.
  if(lag>0){
    return(  c(  rep(NA,lag), x[1:(length(x)-lag)]  )   )
  }else{
    lag = abs(lag)
    return(  c(  x[(lag+1):length(x)], rep(NA,lag)  )   )
  }
}

# === Find rows without NA ====
nonNA_rows <- function(TB){
  non_na_rows = rowSums(is.na(as.data.frame(TB)))==0
  return(non_na_rows)
}

# === Merge Multiple Talbes ===
merge_multiple_tables <- function(TBs, by_var="Date"){
  TB_All = TBs[[1]]
  for( i in 2:length(TBs) ){
    if( !is.null(TBs[[i]]) ){
      TB_All = merge(TB_All, TBs[[i]], by=by_var,all=TRUE) 
    }
  }
  return(TB_All)
}  


# === Robust Standard Errors ===
RobustSE <- function( regs, lag_input=12, error_type="NeweyWest" ){   
  robust_se.list = list()
  for(i in 1:length(regs)){
    if(error_type=="NeweyWest"){
      if(lag_input==1){
        results = unclass(coeftest(regs[[i]]))
      }else{
        results = unclass(coeftest(regs[[i]], vcov. = NeweyWest, lag=lag_input))
      }
    }else{
      # just typical robust standard errors
      results = unclass(coeftest(regs[[i]], vcov. = vcovHC(regs[[i]], type = 'HC0')))
    }
    robust_se.list[[i]]    <-  results[,2]
  }
  return( robust_se.list )
}

# === Extract the standard deviations ===
extract_standard_deviations <- function(regs){
  N = regs[[1]]$rank    # Note: 
  sd_output = list()
  for(j in 1:length(regs)){
    sd_output[[j]] = summary(regs[[j]])$coefficients[1:N,2]
  }
  return(sd_output)
}

# === Standardize a vector ===
standardize <- function( x, keep_positive=FALSE ){   
  x_out = (x-mean(x,na.rm=TRUE))/sd(x,na.rm = TRUE)
  if(keep_positive){
    x_out = (x-min(x,na.rm=TRUE))/sd(x,na.rm = TRUE)
  }
  return(x_out)
}

# === Remove outliers ====
process_outliers <- function(x, provide_index=FALSE, lambda=0.5, return_remaining_index=FALSE){
  x <- ts( x, start= c(1991,1) , frequency=365)
  result <- tsoutliers(x, iterate = 0, lambda = lambda)
  if(provide_index){
    print( paste0(length(result$index), " outliers detected!" ) )
    if(return_remaining_index){
      return(setdiff( seq(1,length(x)) , result$index))
    }else{
      return(result$index)
    }
  }else{
    x[result$index] = result$replacements
    print( paste0(length(result$index), " outliers detected and processed!" ) )
    return( as.numeric(x) )
  }
}

# ====== Residualize Results ======
residualize <- function(x, reference){
  index = !is.na(x) & !is.na(reference)
  reg = lm( x[index] ~ reference[index] )
  residual = x - reg$coefficients[2]*reference
  return( residual - min(residual,na.rm=TRUE) )
}

# === Numerical Derivative ===
derivative_fun <- function(x_vec, y_vec){
  N = length(y_vec)
  dy = y_vec*0
  dy[2:N] = (y_vec[2:N]-y_vec[1:(N-1)])/(x_vec[2:N]-x_vec[1:(N-1)])
  dy[1] = (y_vec[2]-y_vec[1])/(x_vec[2]-x_vec[1])
  return(dy)
}

# === Function for Data Smoothing.===
library(fda)
data_smoothing <- function( x, y, smooth_order=4 ){
  N = length(x)
  nbasis = N +  smooth_order - 2
  wbasis <- create.bspline.basis( range(x), nbasis, smooth_order)
  
  cvec0 <- matrix(0,nbasis,1)
  Wfd0  <- fd(cvec0, wbasis)
  
  #  set up functional parameter object
  Lfdobj    <- 2         #  penalize curvature of acceleration
  lambda    <- 10^(-0.5)  #  smoothing parameter
  growfdPar <- fdPar(Wfd0, Lfdobj, lambda)
  
  weights = c( 1000, rep(1, length(x)-1) )
  
  result = tryCatch( smooth.monotone(x, y, growfdPar, weights), error=function(e){ return("Error") } )
  
  if( class(result)!="monfd" ){   # if the monotonic smoother cannot work, that normally is because too many fluctuations
    fitted_values = lowess(x, y)$y
    fitted_values[1] = y[1]
  }else{
    beta = result$beta
    fitted_values =  beta[1] + beta[2]*eval.monfd(x, result$Wfdobj)
  }
  return( fitted_values )
}


# defining transparent colors 
t_col <- function(color, transparency_percent = 50, name = NULL) {
  #      color = color name
  #    percent = % transparency
  #       name = an optional name for the color
  ## Get RGB values for named color
  gen_color <- function(color_ind){
    rgb.val <- col2rgb(color_ind)
    ## Make new color using input color as base and alpha set by transparency
    t.col <- rgb(rgb.val[1], rgb.val[2], rgb.val[3], maxColorValue = 255,
                 alpha = (100 - transparency_percent) * 255 / 100,
                 names = name)
    ## Save the color
    return(t.col)
  }
  if(length(color)==1){
    return( gen_color(color) )
  }else{
    colors_vec = rep(gen_color(color[1]),length(length(color)))
    for(i in 1:length(color)){
      colors_vec[i] = gen_color(color[i])
    }
    return(colors_vec)
  }
}

# Winsorize function
winsorize <- function(x, lower_quantile=0.01, upper_quantile=0.99){
  x[x<quantile(x,lower_quantile,na.rm=TRUE)] = quantile(x,lower_quantile,na.rm=TRUE)
  x[x>quantile(x,upper_quantile,na.rm=TRUE)] = quantile(x,upper_quantile,na.rm=TRUE)
  return(x)
}



# ========= Plot ========
#' A Self-Defined Plot Function that Simplifies Plotting with multiple series
#' yseries_input = MyPlot( yseries_input = data.frame(seq(1:10),rnorm(10),rnorm(10) ), LegendNames=c( "First Random Sequence", "Second Random Sequence" ) )
MyPlot <- function(  x=NULL,  yseries_input, standard_errors=NULL, CI_multiplier=1.96, CI_transparency=80, CI_linewidth_multiplier=0.2, PlotScale=1.2, Linewidth=2, LegendPosition="topleft", LegendNames=NA, main="", xlab="", ylab="", xlim=NA, ylim=NA, colors=NA, cex.lab=1, cex.axis=1, cex.main=1.1,  mgp = c(2.2, 0.8, 0), line_types=NA, NA_elimination=TRUE, legend_background=FALSE, abline_v=NULL, abline_h=NULL, xaxt="s", yaxt="s" ){
  # Note: x is a vector, and yseries_input is either a dataframe or a vector
  if(sum(is.na(colors))>0){
    colors = rep(c( "blue", "red", "purple", "azure4", "darkslategray4", "goldenrod2", "cyan" ), 2)
  }
  if(sum(is.na(line_types))>0){
    line_types = rep( seq(1,6), 2 )
  }
  yseries_input = as.data.frame(yseries_input)
  N.dim = ncol( yseries_input )
  if( (is.null(x) > 0) ){   # If there is no input from x and only one column is supplied from yseries_input
    if(  ncol(yseries_input)==1 ){
      x =  seq( 1:nrow(yseries_input) )
    }else{
      x = yseries_input[,1]
      yseries_input = yseries_input[ , 2:N.dim ]
    }
  }
  DT = cbind( x, yseries_input )
  DT = as.data.frame(DT)
  NumNAs =  apply( DT, 1, function(z) sum(is.na(z)))  # Eliminate NAs
  Num_Non_NAs = apply( DT, 1, function(z) sum(!is.na(z))) 
  if(NA_elimination){ # eliminate all the rows with at least one NAs
    DT = DT[NumNAs<=0, ]
  }else{ # eliminate only rows with all NAs
    DT = DT[Num_Non_NAs>0, ]
  }
  DT = DT[ order(DT$x),   ]  # Order the table by x
  yseries = DT[ , 2:ncol(DT) ]
  N.dim = ncol(DT)
  if( sum(is.na(ylim))>0 | length(ylim)<2 ){
    ylim = c( min(yseries,na.rm=TRUE), min(yseries,na.rm=TRUE) + (max(yseries,na.rm=TRUE)-min(yseries,na.rm=TRUE))*PlotScale )  # y axes limit
  }
  if( sum(is.na(xlim))>0 | length(xlim)<2 ){
    xlim = c( min(DT[,1],na.rm=TRUE), max(DT[,1],na.rm=TRUE) )  # y axes limit
  }
  if(length(Linewidth)<N.dim-1){
    Linewidth_vec = rep( Linewidth, N.dim-1 )
  }else{
    Linewidth_vec = Linewidth
  }
  if(length(Linewidth_vec)>=3){
    Linewidth_vec[3] = 1.5*Linewidth_vec[3]
  }
  plot( DT[,1], DT[,2],  type="l", col=colors[1], lty=line_types[1], xlab=xlab,  ylab=ylab, main=main, lwd=Linewidth_vec[1], xlim=xlim, ylim=ylim , mgp = mgp, cex.lab=cex.lab, cex.axis=cex.axis, cex.main=cex.main, xaxt=xaxt, yaxt=yaxt)
  if( N.dim>2 ){  # More than 1 series
    for( i in 2:(N.dim-1) ){
      lines(DT[,1] , DT[,i+1],  col=colors[i], lwd=Linewidth_vec[i], lty=line_types[i] )
    }
  }
  if(!is.null(standard_errors)){
    colors_shaded = t_col(colors, transparency_percent = CI_transparency)
    standard_errors = as.data.frame(standard_errors)
    for( i in 1:(N.dim-1) ){
      lines(DT[,1] , DT[,i+1]+CI_multiplier*standard_errors[,i],  lty=line_types[i], col=colors[i], lwd=CI_linewidth_multiplier*Linewidth_vec[i] )
      lines(DT[,1] , DT[,i+1]-CI_multiplier*standard_errors[,i],  lty=line_types[i], col=colors[i], lwd=CI_linewidth_multiplier*Linewidth_vec[i] )
      polygon(c(DT[,1], rev(DT[,1]) ), c( DT[,i+1]+CI_multiplier*standard_errors[,i], rev(DT[,i+1]-CI_multiplier*standard_errors[,i]) ), col=colors_shaded[i], border = NA)
    }
  }
  if( !is.null(abline_v) || !is.null(abline_h) ){
    abline(v=abline_v, h=abline_h, lty=2)
  }
  if( sum(!is.na(LegendNames))>0 ){  # if legend name is provided
    if(legend_background){
      legend( LegendPosition , legend = LegendNames, bg="white", bty="o", lty= line_types[seq(1, N.dim-1)] , col=colors[seq(1, N.dim-1)], lwd=Linewidth*rep(1,N.dim-1)  )
    }else{
      legend( LegendPosition , legend = LegendNames,  bty = "n", lty= line_types[seq(1, N.dim-1)]  , col=colors[seq(1, N.dim-1)], lwd=Linewidth*rep(1,N.dim-1)  )
    }
  }
}

normalize <- function(x){
  return(  (x - mean(x, na.rm=TRUE)) / sd(x,na.rm=TRUE)  )
}


