# Two variables are defined outside this file but determine the algorithm output. 
# 1. option in {"main_paper", "general_belief"}. This controls whether to process data for the main paper or for general belief
# 2. crisis_def in {"bank_credit_GDP_change", "bank_equity_change"}.  This controls whether crises are defined based on bank credit/GDP or bank equity changes. 

delta=0.1  # This it the depreciation parameter that is the same across all models. 
# parameters for the three versions of models. 
alpha = 0.05  # This is the fire-sale loss parameter that is the same across all models. 
sigmaK1=0.055
sigmaK2=0.03
sigmaK3=0.030

# ------------- Basic Functions ---------------------
cbind_table_list <- function(TBs){
  TB = TBs[[1]]
  if(length(TBs)>1){
    for(iter in 1:(length(TBs)-1)){
      TB = rbind(TB, TBs[[iter+1]])
    }
  }
  TB[,T:=(1:nrow(TB))/12]
  return(TB)
}
gen_basic_definitions <- function(TB){
  # TB[ , bank_credit_GDP := bank_credit/GDP ]   # Note: this definition is equivalent
  TB[ , bank_credit_GDP := w*(xK-1)*p/(productivity) ]
  TB[ , total_bank_equity := w*p*K ]
  # Important: scale by the standard deviations
  TB[ , bank_credit_GDP := bank_credit_GDP/sd(bank_credit_GDP) ]
  TB[ , credit_spread := credit_spread/sd(credit_spread) ]
  return(TB)
}
# Then define some risk premium measures. 
gen_risk_premium_measures <- function(TB, sigmaK){
  TB[, risk_premium:=lambda*(kappap+alpha)/(1-xK*kappap-alpha*(xK-1)) + (vol_of_p+sigmaK)^2*xK]
  TB[, total_risk_unadjusted:=lambda*(kappap+alpha)^2 + (vol_of_p+sigmaK)^2 ]
  TB[, total_bank_equity_risks:=(total_risk_unadjusted) * xK^2 ]
  TB[,dw_quadratic_var:=lambda*(xK*kappap+alpha*pmax(xK-1,0))^2 + (vol_of_p+sigmaK)^2*xK^2 ]
  TB[,total_Sharpe:=risk_premium/sqrt(total_risk_unadjusted)]  # This is the total Sharpe ratio.
  return(TB)
}

gen_crisis <- function(TB, cutoff=NA){
  TB[ , Year:= floor(T) ]
  # Define financial crisis based on equity returns.
  gen_non_clustered_crisis <- function( crisis_vec ){
    diff_vec = diff(which(crisis_vec==1))
    crisis_sparse = crisis_vec
    crisis_last = which(crisis_vec)[1]
    for( index in which(crisis_vec)[2:length(diff_vec)] ){
      if(index-crisis_last<0*12){   # 3 years of non consecutive crises
        crisis_sparse[index] = 0
      }else{
        crisis_sparse[index] = 1
        crisis_last = index
      }
    }
    return(crisis_sparse)
  }
  credit_monthly_growth = c(diff(TB$bank_credit_GDP), 0) / TB$bank_credit_GDP
  equity_monthly_change = TB$equity_monthly_change
  solve_for_cutoff <- function(cutoff){
    if(crisis_def == "bank_credit_GDP_change"){
      crisis_vec = credit_monthly_growth < cutoff
    }else{   # equity crisis
      crisis_vec = equity_monthly_change < cutoff
    }
    crisis_sparse = gen_non_clustered_crisis(crisis_vec)
    DT = data.table( Year=TB$Year, crisis_sparse )
    crisis_sparse_yearly = DT[ , list(crisis_sparse=mean(crisis_sparse)>0), by=Year ]$crisis_sparse
    return( mean(crisis_sparse_yearly) - 0.04 )
  }
  if(is.na(cutoff)){
    result = uniroot(solve_for_cutoff, lower=quantile(credit_monthly_growth,0.001), upper=quantile(credit_monthly_growth,0.5)   )
    cutoff=result$root
  }
  if(crisis_def == "bank_credit_GDP_change"){
    print( paste0("Crisis cut off for bank credit growth is ", round(cutoff,digits=2) ) )
    TB[ , crisis := gen_non_clustered_crisis(credit_monthly_growth < cutoff) ]
  }else{  # equity crisis
    print( paste0("Crisis cut off for bank equity growth is ", round(cutoff,digits=2) ) )
    TB[ , crisis := gen_non_clustered_crisis(equity_monthly_change < cutoff) ]
  }
  return(TB)
}
m_fun <- function(x){
  # return(  x[ floor(length(x)/2)+1 ]  )
  return(  first(x)  )
}
gen_yearly_data <- function(TB){
  TB[ , Year:= floor(T) ]
  TB[ , p_yearly_return:= c( rep(NA,12), p[13:nrow(TB)]/p[1:(nrow(TB)-12)] - 1    ) ]
  TB[ ,p_vol_empirical := c(NA, roll_sd( p[2:nrow(TB)]/p[1:(nrow(TB)-1)] - 1 , width=12)) ]
  TB[is.na(p_vol_empirical) ,p_vol_empirical := mean_fun(p_vol_empirical) ]  # For the initial 12 NA observations, just replace them with average volatility. 
  TB[ ,p_vol_empirical := p_vol_empirical/mean_fun(p_vol_empirical) ]
 TB[ , K_monthly_growth := c(rep(0,1), logK_vec_original[2:nrow(TB)]-logK_vec_original[1:(nrow(TB)-1)] )  ]
  TB[ , K_monthly_growth := winsorize(K_monthly_growth, lower_quantile=0.001, upper_quantile=0.999)  ]
  TB[, capital_return_monthly :=  c( rep(NA,1) , K_monthly_growth[2:nrow(TB)] + log(p[2:nrow(TB)]/p[1:(nrow(TB)-1)]) )  ]
  # Define the monthly return volatilty, in yearly unit (i.e., think about the continuous-time limit of the volatility on sample path)
  TB[, capital_return_vol_simulation := c( rep(NA,12) , 12*roll_sd( capital_return_monthly[13:nrow(TB)] , width=12)  )  ]
  TB[is.na(capital_return_vol_simulation) , capital_return_vol_simulation := mean_fun(capital_return_vol_simulation) ]
  TB_qunatities = TB[ , list( Year, dN, crisis, total_bank_equity )  ]
  TB_yearly_quantities = TB_qunatities[, lapply(.SD, mean,na.rm=TRUE), by=Year]
  # deal with some outliers due to numerical issues
  TB[rK_monthly_from_sim>quantile(TB$rK_monthly_from_sim,0.999,na.rm=TRUE)]$rK_monthly_from_sim = NA
  TB[,rK_yearly:= exp(rollsum( log(1+rK_monthly_from_sim), 12, fill=NA, align="right")) - 1  ]
  TB_yearly_prices = TB[ , list(  Year, w, xK, lambda, lambda_rational, underlying_lambda, K, GDP, productivity, bank_equity, vol_of_p, dB_premia, bank_credit,
                                  p, credit_spread, rf, rK, rd, equity_excess_return,  sharpe_ratio, investment_rate,  capital_excess_return, p_vol_empirical, kappap, p_yearly_return, 
                                  bank_credit_GDP, rK_yearly, logK_vec_original, total_Sharpe, risk_premium, total_risk_unadjusted, capital_return_vol_simulation) ]
  # Note: the variable "investment rate" maps to phi(mu^K) in the model, which is the cost of investment, or the real resources cost by investment. 
  TB_yearly_prices = TB_yearly_prices[ , lapply(.SD, first), by=Year ]
  TB_yearly = merge(TB_yearly_quantities, TB_yearly_prices, by="Year")
  TB_yearly[ , crisis:=crisis>0 ]
  TB_yearly[ , dN:=dN>0 ]
  return( TB_yearly[ Year>=1 ] )
}

processing_simulation_data <- function(TB_yearly){
  # Note: the input table should be at yearly frequency
  TB_yearly[ , bank_credit_GDP_pre_year :=  c( mean(bank_credit_GDP),  bank_credit_GDP[1:(nrow(TB_yearly)-1)]   )   ]
  TB_yearly[, bank_equity_excess_return:= equity_excess_return]
  TB_yearly[ , sigma_of_p_standardized := vol_of_p/mean(vol_of_p)  ]
  TB_yearly[ , total_vol_standardized :=  sqrt(total_risk_unadjusted) / mean_fun(sqrt(total_risk_unadjusted)) ]   # Standardize the theory-implied total volatility 
  weights = 0.8^c(10:0)
  TB_yearly[ , historical_vol_p := roll_sd(p, 10, weights ) ]
  TB_yearly[ is.na(historical_vol_p)]$historical_vol_p = mean(TB_yearly$historical_vol_p,na.rm=TRUE)
  TB_yearly[ , Kp := K*p ]
  TB_yearly[ , capital_growth := c( K[2:nrow(TB_yearly)]/K[1:(nrow(TB_yearly)-1)]-1, 0 ) ]
  TB_yearly[ , investment_rate_3Y:=  c( rollsum( investment_rate, 3 ), rep( 3*mean(TB_yearly$investment_rate) ,2)) ]
  index = 1:(nrow(TB_yearly)-1)
  # Next-year capital return
  # Average credit spread: the average last 5 year value of credit spread, following Krishnamurthy and Muir definition
  TB_yearly[ , avg_credit_spread_5Y := c( rep(0,5-1), rollmean(credit_spread, k=5) )  ]
  TB_yearly[,  froth:= avg_credit_spread_5Y<median(avg_credit_spread_5Y)]  # This is the definition in KM 2017.
  crises_index = which( TB_yearly$crisis==1 )
  distress_index = which( TB_yearly$dN==1 )
  pre_crises_years = 5
  index_before_crises = crises_index
  index_before_distress = distress_index
  for( i in 1:pre_crises_years ){
    index_before_crises = c(  index_before_crises,  pmax(crises_index-i,1) )
    index_before_distress = c(  index_before_distress,  pmax(distress_index-i,1) )
  }
  TB_yearly[, before_crises_1_to_5Y:=0]
  TB_yearly[ index_before_crises,before_crises_1_to_5Y:=1]
  TB_yearly[ , before_crises:=0]
  TB_yearly[ crises_index-1, before_crises:=1]
  TB_yearly[  , large_credit := bank_credit_GDP>=quantile(bank_credit_GDP,0.9)  ]
  TB_yearly[  , before_crises_and_large_credit := large_credit*before_crises  ]
  TB_yearly[  , credit_growth_past_year := c(rep(0,12), bank_credit[13:nrow(TB_yearly)]/bank_credit[1:(nrow(TB_yearly)-12)]-1)  ]
  TB_yearly[  , credit_growth := c(0, (bank_credit[2:nrow(TB_yearly)]/bank_credit[1:(nrow(TB_yearly)-1)]-1) )  ]
  TB_yearly[  , credit_growth_next_year := c( bank_credit[2:nrow(TB_yearly)]/bank_credit[1:(nrow(TB_yearly)-1)]-1, 0 )  ]
  TB_yearly[  , capital_excess_return_normalized := capital_excess_return/mean(capital_excess_return)*0.059  ]  # Note: 0.2 is the standard deviation of equity returns.
  TB_yearly[  , capital_crash := capital_excess_return<quantile(capital_excess_return,0.05)  ]
  
  TB_yearly[ , credit_spread_next_year := c( credit_spread[2:nrow(TB_yearly)] , rep(0,1) ) ]
  TB_yearly[ , credit_spread_change := c( credit_spread[2:nrow(TB_yearly)] - credit_spread[1:(nrow(TB_yearly)-1)], 0 ) ]
  TB_yearly[ , credit_spread_last_year :=  c( rep(0,1), credit_spread[1:(nrow(TB_yearly)-1)] ) ]
  TB_yearly[ , GDP_yearly_change:= c( GDP[2:nrow(TB_yearly)]/GDP[1:(nrow(TB_yearly)-1)]-1, rep(0,1))  ]
  TB_yearly[ , GDP_yearly_change_past:= c(rep(0,1), GDP[2:nrow(TB_yearly)]/GDP[1:(nrow(TB_yearly)-1)]-1)  ]
  TB_yearly[ , GDP_3Y_change:= c( GDP[(1+3):nrow(TB_yearly)]/GDP[1:(nrow(TB_yearly)-3)]-1, rep(0,3)) ]
  TB_yearly[ , GDP_5Y_change:= c( GDP[(1+5):nrow(TB_yearly)]/GDP[1:(nrow(TB_yearly)-5)]-1, rep(0,5)) ]
  
  # Important: the changes are all forward-looking. 
  TB_yearly[ , credit_2Y_change:= c( bank_credit[(1+2):nrow(TB_yearly)]/bank_credit[1:(nrow(TB_yearly)-2)]-1, rep(0,2)) ]
  TB_yearly[ , credit_3Y_change:= c( bank_credit[(1+3):nrow(TB_yearly)]/bank_credit[1:(nrow(TB_yearly)-3)]-1, rep(0,3)) ]
  TB_yearly[ , credit_5Y_change:= c( bank_credit[(1+5):nrow(TB_yearly)]/bank_credit[1:(nrow(TB_yearly)-5)]-1, rep(0,5)) ]
  TB_yearly[ , credit_8Y_change:= c( bank_credit[(1+8):nrow(TB_yearly)]/bank_credit[1:(nrow(TB_yearly)-8)]-1, rep(0,8)) ]
  TB_yearly[ , equity_3Y_change:= c( bank_equity[(1+3):nrow(TB_yearly)]/bank_equity[1:(nrow(TB_yearly)-3)]-1, rep(0,3)) ]
  TB_yearly[ , equity_1Y_change:= c( bank_equity[(1+1):nrow(TB_yearly)]/bank_equity[1:(nrow(TB_yearly)-1)]-1, rep(0,1)) ]  
  
  TB_yearly[ , post_crises_5Y :=  c( rep(0,4), rollsum(crisis, 5) )>0   ] # An indicate of within 5 years after the next crisis.
  TB_yearly[ , post_crises_3Y :=  c( rep(0,2), rollsum(crisis, 3) )>0   ]
  TB_yearly[ , crises_next_5Y :=  c( rollsum(crisis, 5), rep(0,4) )>0   ]
  TB_yearly[ , recession := (GDP_yearly_change<quantile(GDP_yearly_change,0.08)) & (!crises_next_5Y)  ]
  median_GDP_change_in_crisis = median(TB_yearly[crisis==TRUE]$GDP_yearly_change, na.rm=TRUE)
  TB_yearly[ , GDP_yearly_change_next := c( GDP_yearly_change[2:nrow(TB_yearly)],0 ) ]
  TB_yearly[ , before_severe_crises :=   before_crises*(GDP_yearly_change_next<median_GDP_change_in_crisis)     ]
  TB_yearly[ , before_mild_crises :=   before_crises*(GDP_yearly_change_next>median_GDP_change_in_crisis)     ]
  
  TB_yearly[ , bank_equity_change_around_crisis:=0 ]
  TB_yearly[ , Years_around_crisis := -100  ] # Check -4 and +6 years range.
  TB_yearly[ , Years_around_crisis:=as.integer(Years_around_crisis) ]
  counter_total = sum(TB_yearly$crisis)
  counter = 0
  for( index in  which(TB_yearly$crisis) ){
    counter = counter + 1
    if(counter%%(counter_total/10)==0){
      print( paste0("Processing years around crisis:", round(counter/counter_total*100,digits = 2), "%" ) )
    }
    index_for_change = max(1,index-4):min(index+8,nrow(TB_yearly))
    index_for_change = index_for_change[  TB_yearly[index_for_change,]$Years_around_crisis==-100   ]
    if( is.element(0, index_for_change - index) ){   # At least having the starting point of the crisis
      TB_yearly[index_for_change, Years_around_crisis := index_for_change - index ]
      TB_yearly[index_for_change,]$bank_equity_change_around_crisis = log(TB_yearly$total_bank_equity[index_for_change]) - log(TB_yearly$total_bank_equity[index])
    }
  } 
  TB_yearly[ Years_around_crisis==-100 , Years_around_crisis:= NA ]
  TB_yearly[ , pre_crisis := Years_around_crisis<0 ]
  TB_yearly[  is.na(pre_crisis), pre_crisis:=FALSE ]
  TB_yearly[ , crisis_next_year := c(  crisis[2:nrow(TB_yearly)], rep(FALSE,1)  )  ]
  
  # Then investment and consumption growth
  TB_yearly[,consumption:= (productivity - investment_rate)*K ]
  TB_yearly[,consumption_growth := c(0, consumption[2:nrow(TB_yearly)]/consumption[1:(nrow(TB_yearly)-1)]-1 ) ]
  TB_yearly[,investment:=investment_rate*K]
  TB_yearly[,investment_growth:= c(0, investment[2:nrow(TB_yearly)]/investment[1:(nrow(TB_yearly)-1)]-1 )]
  return(TB_yearly)
}


print("Generate yearly data ...")


# ---------------- Processing Data --------------
number_of_files = 4
if(option=="main_paper"){ 
  print("********* Procesing Data for the Main Paper *********")
  # Generate data used for the main paper
  TBs = list()
  print("Reading benchmark model simulated data ...")
  for(iter in 1:number_of_files){
    TBs[[iter]] = as.data.table(read_xlsx(paste0("simulated data/smolayak_benchmark_sim",iter,".xlsx"), sheet=1))  # This is the one without belief updating
  }
  TB_benchmark_raw = cbind_table_list(TBs)
  print("Reading Bayesian model simulated data ...")
  for(iter in 1:number_of_files){
    TBs[[iter]] = as.data.table(read_xlsx(paste0("simulated data/smolayak_Bayesian_sim",iter,".xlsx"), sheet=1))  # This is the one without belief updating
  }
  TB_Bayesian_raw = cbind_table_list(TBs)
  print("Reading Diagnostic model simulated data ...")
  for(iter in 1:number_of_files){
    TBs[[iter]] = as.data.table(read_xlsx(paste0("simulated data/smolayak_Diagnostic_sim",iter,".xlsx"), sheet=1))  # This is the one without belief updating
  }
  TB_Diagnostic_raw = cbind_table_list(TBs)
  # Generate risk premium measures
  TB_benchmark_raw  = gen_risk_premium_measures(TB_benchmark_raw, sigmaK1)
  TB_Bayesian_raw   = gen_risk_premium_measures(TB_Bayesian_raw, sigmaK2)
  TB_Diagnostic_raw = gen_risk_premium_measures(TB_Diagnostic_raw, sigmaK3)
  # Generate basic definitions 
  TB_benchmark_raw = gen_basic_definitions(TB_benchmark_raw)
  TB_Bayesian_raw = gen_basic_definitions(TB_Bayesian_raw)
  TB_Diagnostic_raw = gen_basic_definitions(TB_Diagnostic_raw)
  # Then process the yearly data. 
  TB_benchmark = processing_simulation_data( gen_yearly_data( TB_benchmark_raw) )
  TB_Bayesian = processing_simulation_data(gen_yearly_data(TB_Bayesian_raw))
  TB_Diagnostic = processing_simulation_data(gen_yearly_data(TB_Diagnostic_raw))
  TB = TB_Bayesian
  
  # Simulateneous generate regressions on three cases
  regs_combo <- function(gen_regs, number_of_cases=3){
    regs_benchmark = gen_regs(TB_benchmark)
    regs_Bayesian = gen_regs(TB_Bayesian)
    regs_output = c( regs_benchmark,  regs_Bayesian)
    if(number_of_cases==3){
      regs_Diagnostic = gen_regs(TB_Diagnostic)
      regs_output = c(regs_output, regs_Diagnostic)
    }
    return(regs_output)
  }
}else{
  print("********* Procesing Data for the General Belie Case (Appendix) *********")
  # Then preprocess for the general belief. 
  TBs = list()
  # Bayesian model is the benchmark for comparison with optimistic and pessimistic models. 
  print("Reading Bayesian model simulated data ...")
  for(iter in 1:number_of_files){
    TBs[[iter]] = as.data.table(read_xlsx(paste0("simulated data/smolayak_Bayesian_sim",iter,".xlsx"), sheet=1))  # This is the one without belief updating
  }
  TB_Bayesian_raw = cbind_table_list(TBs)
  print("Reading overoptimistic model simulated data ...")
  for(iter in 1:number_of_files){
    TBs[[iter]] = as.data.table(read_xlsx(paste0("simulated data/smolayak_optimistic_sim",iter,".xlsx"), sheet=1))  # This is the one without belief updating
  }
  TB_optimistic_raw = cbind_table_list(TBs)
  print("Reading overpessimistic model simulated data ...")
  for(iter in 1:number_of_files){
    TBs[[iter]] = as.data.table(read_xlsx(paste0("simulated data/smolayak_pessimistic_sim",iter,".xlsx"), sheet=1))  # This is the one without belief updating
  }
  TB_pessimistic_raw = cbind_table_list(TBs)
  
  # Then process yearly data. 
  TB_optimistic = processing_simulation_data( gen_yearly_data( gen_basic_definitions(TB_optimistic_raw) ) )
  TB_pessimistic = processing_simulation_data( gen_yearly_data( gen_basic_definitions(TB_pessimistic_raw) ) )
  TB_Bayesian = processing_simulation_data( gen_yearly_data( gen_basic_definitions(TB_Bayesian_raw) ) )
}

print("------------- Processing raw data is finished! --------------")




