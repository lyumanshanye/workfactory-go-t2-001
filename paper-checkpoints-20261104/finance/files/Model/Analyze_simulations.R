# ******** Study the Simulation Results From the Model *******
### Note: the default is that when you call this file, the path is the current file path. "FigurePath" and "TablePath" are paths for figure and table outputs. 

# ------------  Pre-Process the Model Simulated Data -----------------
# Then call the module that processes
option="main_paper"   #pre-process for the main paper.  Otherwise, select "general_belief", and then the file will process results for general beliefs, and those will be in the appendix.
crisis_def = "bank_credit_GDP_change"  # Define crisis as based on bank credit/GDP severely dropping.  
source("Codes_Model/preprocessing_simulation_data.R")  # This file needs the input, "option", and "crisis_def"
# Then select whether to generate tables to files. 
gen_tables = TRUE

# Write Stata output file for regression analysis.  
save.dta13(TB_Diagnostic, "simulated data/diagnostic_full_yearly.dta")
save.dta13(TB_Bayesian, "simulated data/bayesian_full_yearly.dta")

#==================== Table 3 Panel A: Main regression results ===================
print("************ Generating Table 3 Panel A ************ ")
reg_output_and_credit_spread <- function( TB ){
  TB[ , crisis_interact_credit_spread_change :=  credit_spread_change*crisis]
  TB[ , crisis_interact_credit_spread_control :=  credit_spread_last_year*crisis]
  TB[  , crisis_interact_bank_credit:= bank_credit_GDP*crisis ]
  regs=list()
  regs[[1]] = lm( 100*GDP_3Y_change ~  crisis_interact_credit_spread_change  , data=TB )
  regs[[2]] = lm( 100*GDP_3Y_change ~  crisis_interact_bank_credit  , data=TB )
  return(regs)
}
latex_reg_output_and_credit_spread_all <- function(regs, regs_data, dependent_var_name="GDP Growth", vol_vec=c(0.47, 0.16, 0.30)){
  N_columns = length(regs)+length(regs_data)
  results=capture.output(stargazer( c(regs, regs_data) , df = FALSE, digits = 2, omit.stat = c("rsq", "f", "ser","n","adj.rsq") , omit=c("Constant"), star.cutoffs = c(0, 0, 0),
                                    se = list( 0, 0, 0, 0, 0, 0, 0, 0)  ,
                                    title=paste0(dependent_var_name, " and Credit Spread"),
                                    label = paste0("Severity regression on ", dependent_var_name)  ,
                                    dep.var.caption= paste0("\\textit{Dependent variable: ", dependent_var_name, " from $t$ to $t+3$}") ,
                                    dep.var.labels =  rep("",N_columns) , 
                                    column.labels   = c("Static Belief","Bayesian","Diagnostic", "Data"),
                                    covariate.labels = c("$\\Delta$credit spread$_t*$crisis$_t$", 
                                                         "$(\\frac{\\text{bank credit}}{\\text{GDP}})_t*$crisis$_t$" ),
                                    column.separate = rep(length(regs_data),N_columns/length(regs_data)), 
                                    add.lines =  list(  c( "Observations", rep("",length(regs)), rep(641,length(regs_data))  )  ),
                                    notes="To be replaced", notes.append=FALSE, notes.align="l",no.space = TRUE,
                                    column.sep.width = "0pt"
  ))
  results[12] = "\\\\[-1.8ex]"
  results[length(results)-2] =  paste0("\\multicolumn{", N_columns+1 ,"}{p{0.95\\textwidth}}{\\footnotesize \\textit{Note}: 
                                       Model and data regressions are normalized so that the coefficients reflect the impact of one sigma change in spreads, and bank credit/GDP. 
                                       }")
  writeLines(results, paste0(TablePath,"crisis_aftermath/",gsub(" ", "_", dependent_var_name, fixed = TRUE), "_all.tex" ) )
  print(results)
}
regs_benchmark = reg_output_and_credit_spread(TB_benchmark)
regs_Bayesian = reg_output_and_credit_spread(TB_Bayesian)
regs_Diagnostic= reg_output_and_credit_spread(TB_Diagnostic)
regs_data = regs_benchmark
regs_data[[1]]$coefficients[2]=-7.46
regs_data[[2]]$coefficients[2]= -0.95
if(gen_tables){
  regs = c(regs_benchmark, regs_Bayesian, regs_Diagnostic  )
  latex_reg_output_and_credit_spread_all( regs,  regs_data)
}


#  ================== Table 3 Panel B: Bank Credit and Capital Excess Returns  ==================
print("************ Generating Table 3 Panel B ************ ")
reg_capital_return <- function(TB){
  TB_yearly = TB
  # TB_yearly[ , credit_ratio:= credit_ratio/sd(credit_ratio)  ]
  regs = list()
  regs[[1]] = lm( capital_excess_return_normalized ~ bank_credit_GDP, data = TB_yearly)
  return(regs)
}
regs_data = reg_capital_return(TB_benchmark)
regs_data[[1]]$coefficients[2] = -0.02
latex_reg_capital_return_slides <- function(regs, version = "Static Belief", vol_vec = c(0.0095)){
  results=capture.output(stargazer( c(regs, regs_data) , df = FALSE, digits = 2, omit.stat = c("rsq", "f", "ser","n","adj.rsq","LL","aic") , omit=c("Constant"), star.cutoffs = c(0, 0, 0),
                                    se = list( 0, c(0,vol_vec[1]) )  ,
                                    title=paste0("Bank Credit Predicting Equity Excess Return in the ", str_replace(version, fixed("Slides"),"") ," Model"),
                                    label = paste0(version, ": bank credit and excess returns")  ,
                                    dep.var.caption=  "\\textit{Dependent variable:}" ,
                                    dep.var.labels =  "Average realized excess return $_{t+1}$" , 
                                    covariate.labels = c("$(\\frac{\\text{bank credit}}{\\text{GDP}})_t$"),
                                    column.separate = c(1, 1), 
                                    add.lines =  list(  c( "Observations", "", "867" )  ),
                                    notes="To be replaced", notes.append=FALSE, notes.align="l",
                                    column.sep.width = "45pt"
  ))
  results[13] = "\\\\[-1.8ex] & (1) Model Simulations  & (2) Data \\\\"
  results[length(results)-2] =  "\\multicolumn{3}{p{0.65\\textwidth}}{\\footnotesize \\textit{Note}: 
  Model excess return is defined as the return to capital minus the risk-free rate. Data excess return is the excess 
equity index return from Online Appendix Table 3 of Baron and Xiong (2017). To ensure comparability, the model return 
to capital has been normalized to equal the standard deviation of returns reported by Baron and Xiong (2017).
}  "
  writeLines(results, paste0(TablePath,"capital_excess_returns/credit_and_capital_return_", version,".tex" ) )
}
latex_reg_capital_return_all <- function(regs, vol_vec = c(0.0095)){
  results=capture.output(stargazer( c(regs, regs_data) , df = FALSE, digits = 2, omit.stat = c("rsq", "f", "ser","n","adj.rsq","LL","aic") , omit=c("Constant"), star.cutoffs = c(0, 0, 0),
                                    se = list( 0, 0, 0, 0 )  ,
                                    title=paste0("Bank Credit Predicting Capital Excess Returns"),
                                    label = paste0("bank credit and excess returns")  , 
                                    dep.var.caption=  "\\textit{Dependent variable:}" ,
                                    dep.var.labels =  "Average realized excess return $_{t+1}$" , 
                                    covariate.labels = c("$(\\frac{\\text{bank credit}}{\\text{GDP}})_t$"),
                                    column.separate = c(1, 1, 1, 1), 
                                    add.lines =  list(  c( "Observations", rep("",3), "867" )  ),
                                    notes="To be replaced", notes.append=FALSE, notes.align="l",
                                    column.sep.width = "10pt", no.space = TRUE
  ))
  results[13] = "\\\\[-1.8ex] & (1) Static Belief & (2) Bayesian & (3) Diagnostic  & (4) Data \\\\"
  results[length(results)-2] =  "\\multicolumn{5}{p{0.9\\textwidth}}{\\footnotesize \\textit{Note}: 
  Model excess return is defined as the return to capital minus the risk-free rate. Data excess return is the excess 
equity index return from Online Appendix Table 3 of Baron and Xiong (2017). To ensure comparability, the model return 
to capital has been normalized to equal the standard deviation of returns reported by Baron and Xiong (2017).
}  "
  writeLines(results, paste0(TablePath,"capital_excess_returns/credit_and_capital_return.tex" ) )
  print(results)
}
regs_benchmark = reg_capital_return(TB_benchmark)
regs_Bayesian = reg_capital_return(TB_Bayesian)
regs_Diagnostic = reg_capital_return(TB_Diagnostic)

if(gen_tables){
  regs = c( regs_benchmark,  regs_Bayesian, regs_Diagnostic )
  latex_reg_capital_return_all( regs )
}

# ================== Table 3 Panel C: Credit Spread Before Crises  ==================
print("************ Generating Table 3 Panel C ************ ")
# Low Credit Spread
reg_crises_low_spread <- function(TB){
  TB[ , crises_post_5Y :=  c( rep(0,4), rollsum(crisis, 5) )>0   ] # An indicate of within 5 years after the next crisis.
  TB[ , crises_next_3Y :=  c( rollsum(crisis, 3), rep(0,2) )>0   ]
  TB[ , before_recession := (GDP_3Y_change<quantile(GDP_3Y_change,0.1)) & (!crises_next_3Y)  ]
  regs=list()
  regs[[1]] = lm( credit_spread ~  before_crises + crises_post_5Y , data=TB )
  # regs[[3]] = lm( credit_spread ~  before_recession , data=TB )
  return(regs)
}
regs_data = reg_crises_low_spread(TB_benchmark)
regs_data[[1]]$coefficients[2] = -0.34
regs_data[[1]]$coefficients[3] = 0

latex_reg_crises_low_spread_all <- function(regs){
  results = capture.output(stargazer( c(regs, regs_data) , df = FALSE, digits = 2, omit.stat = c("rsq", "f", "ser","n","adj.rsq") , omit=c("Constant"), star.cutoffs = c(0, 0, 0),
                                      se = list( 0,0,0,0)  ,
                                      title=paste0("Credit Spread Before Crises in Different Models"),
                                      label = paste0("low spread before crises")  ,
                                      dep.var.caption= paste0("\\textit{Dependent variable: credit spread$_t$}") ,
                                      dep.var.labels =  rep("",2) , 
                                      column.labels   = c("Static Belief","Bayesian", "Diagnostic", "Data"),
                                      covariate.labels = c("pre-crisis indicator",  "within 5 years of last crisis" ),
                                      column.separate = c(1, 1, 1, 1), 
                                      add.lines =  list(  c( "Observations", rep("",3) , "634" )  ),
                                      notes="To be replaced.", notes.append=FALSE, notes.align="l",
                                      column.sep.width = "10pt", no.space = TRUE
  ))
  results[12] = "\\\\[-1.8ex]"
  results[length(results)-2] = " \\multicolumn{5}{p{0.8\\textwidth}}{\\footnotesize \\textit{Note}: regression is:  $ s_t = \\alpha + \\beta \\cdot  1\\{t \\text{ is within 5-year window before a crisis} \\} + controls $. 
  For both model and data, controls include an indicator of within 5 years after the last crisis. Data regression has more controls such as country fixed effect. } \\\  "
  results = results[ -c(17,18) ]
  writeLines(results, paste0(TablePath,"low_spread_before_crises/pre-crisis_spread.tex" ) )
  print(results)
}

regs_benchmark = reg_crises_low_spread(TB_benchmark)
regs_Bayesian = reg_crises_low_spread(TB_Bayesian)
regs_Diagnostic = reg_crises_low_spread(TB_Diagnostic)
stargazer( c(regs_benchmark, regs_Bayesian, regs_Diagnostic) , type = "text")
# output
if(gen_tables){
  regs = c( regs_benchmark, regs_Bayesian, regs_Diagnostic )
  latex_reg_crises_low_spread_all(regs)
}


#  ================== Table 3 Panel D: Predicting Crises  ==================
print("************ Generating Table 3 Panel D ************ ")
reg_crises_predictability <- function(TB, auxiliary=FALSE){
  TB_yearly = TB
  cutoff = 0.5
  TB_yearly[ , froth := credit_spread<=quantile(credit_spread,cutoff) ]
  TB_yearly[ , crisis_next_year :=  c(  crisis[2:nrow(TB_yearly)]>0,  NA  ) ]
  TB_yearly[ , crisis_next_5_year :=  c(  rollsum(crisis,5)>0, rep(0,4) ) ]
  TB_yearly[ , crisis_next_3_year :=  c(  rollsum(crisis,3)>0, rep(0,2) ) ]
  TB_yearly[ , high_credit := bank_credit_GDP>=quantile(bank_credit_GDP,1-cutoff)  ]
  TB_yearly[ , high_credit_past_5y := c( rep(0,4), rollmean(high_credit,5 ) )>0 ]
  TB_yearly[ , capital_crash := capital_excess_return<quantile(capital_excess_return,0.05) ]
  marginal_effect <- function(reg){
    summary_results = summary(margins(reg))
    return(as.numeric(summary_results[2])*100)
  }
  
  regs = list()
  regs[[1]] = glm( crisis_next_3_year ~ froth, family = binomial(), data = TB_yearly)
  regs[[2]] = glm( crisis_next_year ~ bank_credit_GDP, family = binomial(), data = TB_yearly)
  # 
  regs[[1]]$coefficients[2] = marginal_effect(regs[[1]])
  regs[[2]]$coefficients[2] = marginal_effect(regs[[2]])
  return(regs)
}
regs_data = reg_crises_predictability(TB_benchmark)
regs_data[[1]]$coefficients[2] = 18.0
regs_data[[2]]$coefficients[2] = 2.8
latex_reg_crises_predictability_all <- function(regs){
  results=capture.output(stargazer( c(regs, regs_data) , df = FALSE, digits = 2, omit.stat = c("rsq", "f", "ser","n","adj.rsq","LL","aic") , omit=c("Constant"), star.cutoffs = c(0, 0, 0),
                                    se = list( 0, 0, 0, 0, 0, 0, 0, 0 )  ,
                                    title=paste0("Predicting Crises"),
                                    label = paste0("prediction of crises")  ,
                                    dep.var.caption= paste0("\\textit{Dependent variable: Probability of Crisis}") ,
                                    dep.var.labels =  rep("",8) , 
                                    column.labels   = c("Static Belief", "Bayesian", "Diagnostic", "Data"),
                                    covariate.labels = c("Froth$_t$", "$(\\frac{\\text{bank credit}}{\\text{GDP}})_t$"),
                                    column.separate = c(2, 2, 2, 2), 
                                    add.lines =  list(  c( "Observations", rep("",6), c(528,1272)  )  ),
                                    notes="To be replaced", notes.append=FALSE, notes.align="l",
                                    column.sep.width = "10pt", 
                                    no.space = TRUE
  ))
  results[12] = "\\\\[-1.8ex]"
  results[length(results)-2] =  "\\multicolumn{9}{p{0.95\\textwidth}}{\\footnotesize \\textit{Note}: 
  Froth in the model measures if the credit spread is below the median at date $t$.  In the data regression, froth measures if credit spread is below the median over $t-5$ to $t$ (see \\cite{krishnamurthy2017credit}).  In both model and data we run a Logit regression of crisis occurring over the next 5 years on the froth measure and report the probability.  
  Bank credit/GDP is the current ratio of bank credit over GDP.  The data regression of crisis over the next year on bank credit/GDP is from \\cite{schularick2012credit}, and we report the probability of the crisis.
}  "
  writeLines(results, paste0(TablePath,"predictability/predicting_crisis.tex" ) )
  print(results)
}

regs_benchmark = reg_crises_predictability(TB_benchmark)
regs_Bayesian = reg_crises_predictability(TB_Bayesian)
regs_Diagnostic = reg_crises_predictability(TB_Diagnostic)
regs = c( regs_benchmark, regs_Bayesian, regs_Diagnostic )
stargazer( regs, type="text", df = FALSE, digits = 2, omit.stat = c("rsq", "f", "ser") , star.cutoffs = c(0, 0, 0 ), 
           column.labels   = c("Static Belief", "Bayesian", "Diagnostic"), column.separate = rep(length(regs)/3,3), 
           dep.var.labels.include = FALSE, 
           covariate.labels = c("froth last 5 year", "bank credit/GDP"),  dep.var.caption = "Dep var: crisis in the next year" )
if(gen_tables){
  latex_reg_crises_predictability_all( regs )
}

#  ================== TABLE Appendix: Extra Model Moments  ==================
# Level of credit spread. 
# Volatility of credit spread
# Level of the real interest rate
# Volatility of the real interest rate
# Volatility of the output growth 
# Volatility of the consumption growth
# Volatility of investment growth 
# Volatility of bank equity growth 
return_AP_moments <- function(TB){
  return( c(
    sd(TB$rf - TB$rd),   # vol(liquidity premium)
    sd(TB$rf),   # vol(risk-free rate)
    sd(TB$equity_1Y_change),  # vol(annual equity reeturn)
    sd(TB$investment_growth),  # vol(annual investment growth rate)
    sd(TB$consumption_growth),  # vol(consumption growth rate)
    mean_fun(TB$rd),     # vol(risk-free rate)
    mean_fun(TB$total_Sharpe)   # vol(total Sharpe ratio)
  ) )
}
var_names = c("vol(liquidity premium)", "vol(risk-free rate)", "vol(annual bank equity return)", "vol(investment yearly growth rate)", "vol(consumption growth return)", "mean(risk free rate)", "average total Sharpe ratio of capital return"  )
TB_vol = data.frame(var_names,  return_AP_moments(TB_benchmark), return_AP_moments(TB_Bayesian), return_AP_moments(TB_Diagnostic) )
names(TB_vol)<- c("Moments", "Benchmark","Bayesian","Diagnostic")
write_xlsx( TB_vol, paste0(TablePath,"Table5_additional_moments.xlsx") )


