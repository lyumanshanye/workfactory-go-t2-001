// use simulated annual data and produce Tables to related crisis outcomes to fragility measures and 
cd "~/Dropbox/Research/Beliefs and Crises/Replication Package/Model/simulated data"


// *********** For the Bayesian Model. *********** 
use bayesian_full_yearly.dta, clear

tsset Year
ge crisis3y = 0
ge crisis1y = crisis
replace crisis3y = 1 if (crisis1y==1 | f1.crisis1y==1 | f2.crisis1y==1)
ge bank_debt = p*(xK-1)*w*K/GDP
ge bank_debt_truelambda = bank_debt*underlying_lambda

// produce figure 13
quietly probit crisis3y bank_debt
margins , at(bank_debt=(1(1)5)) atmeans
marginsplot, xtitle("Bank Credit/GDP") ytitle("Prob(Crisis in next 3Y)") title("Adjusted Predictions with 95% CIs") graphregion(fcolor(white))
graph export "../../Figures/predictability/Bayesianbasic.pdf", replace

quietly probit crisis3y bank_debt_truelambda
margins , at(bank_debt=(0(0.5)2.5)) atmeans
marginsplot, xtitle("True Lambda * Bank Credit/GDP") ytitle("Prob(Crisis in next 3Y)") title("Adjusted Predictions with 95% CIs") graphregion(fcolor(white))
graph export "../../Figures/predictability/Bayesiantrue.pdf", replace


// *********** For the Diagnostic Model. *********** 
use diagnostic_full_yearly.dta, clear

tsset Year
ge crisis3y = 0
ge crisis1y = crisis
replace crisis3y = 1 if (crisis1y==1 | f1.crisis1y==1 | f2.crisis1y==1)
ge bank_debt = p*(xK-1)*w*K/GDP
ge bank_debt_truelambda = bank_debt*underlying_lambda

// and for diagnostic model, produce figure 14
quietly probit crisis3y bank_debt
margins , at(bank_debt=(1(1.1)5.4)) atmeans
marginsplot, xtitle("Bank Credit/GDP") ytitle("Prob(Crisis in next 3Y)") title("Adjusted Predictions with 95% CIs") graphregion(fcolor(white))
graph export "../../Figures/predictability/Diagnosticbasic.pdf", replace

quietly probit crisis3y bank_debt_truelambda
margins , at(bank_debt=(0(0.6)3.0)) atmeans
marginsplot, xtitle("True Lambda * Bank Credit/GDP") ytitle("Prob(Crisis in next 3Y)") title("Adjusted Predictions with 95% CIs") graphregion(fcolor(white))
graph export "../../Figures/predictability/Diagnostictrue.pdf", replace

graph close



