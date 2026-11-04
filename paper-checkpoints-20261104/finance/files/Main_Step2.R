## Codes for the article "Beliefs and Financial Crises", by Arvind Krishnamurthy and Wenhao Li.
# This is the master file that calls all other files. 
cat("\014")  # Clear setup screen. 
remove(list=ls()) 
# == Setup path
MainPath = paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/Model")
setwd(MainPath) # set the path of this R file as the current path
setwd( "../Figures" )
FigurePath = paste0(getwd(),"/")
setwd( "../Tables" )
TablePath = paste0(getwd(),"/")
setwd(MainPath) # set the path of this R file as the current path
# Then load required packages. 
source("loading_package_and_functions.R")

# ----------- This will generate Table 3, and Table in Appendix A.8 --------
source("Analyze_simulations.R")  

# ----------- This will generate Table 4 --------
source("Analyze_simulations_equity_crash.R")

# ----------- This will generate Table 10 and 11 (Appendix B) --------
source("Analyze_simulations_general_beliefs.R")

# ----------- This will generate Figures in the paper. --------
source("figures_generation.R")











