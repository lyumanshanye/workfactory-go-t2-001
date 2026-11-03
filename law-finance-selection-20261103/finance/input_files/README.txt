
Data and codes for the empirical results in 
"A Unifying Approach to the Empirical Evaluation of Asset Pricing Models"
by Francisco Peñaranda and Enrique Sentana.

In particular, we report empirical evaluations of the following models:

- Table 1: CAPM.

- Table 2: CCAPM.

- Table A1: Epstein-Zin model.

- Table A2: CCAPM with a gross return.

We use the data in Lustig and Verdelhan (2007), where the payoffs to price are the annual excess returns on 8 currency portfolios (1953-2002).
Our codes are written for Gauss.


--------------------------------------


DATA

Files: CPI.txt, FF3a.txt, LV_fac.txt, and LV_port.txt

The files LV_fac and LV_port correspond to the data in Lustig and Verdelhan (2007), available in Adrien Verdelhan's web page:

- LV_fac has 2 pricing factors, Rvwexc and Consumption Growth.

- LV_port has 8 portfolios to be priced.

The files CPI and FF3a are used to construct the gross return in Table A2, which is not priced in Lustig and Verdelhan (2007):

- FF3a contains the 3 Fama-French factors and the riskfree rate, from Kenneth French's web page. We only use the last column.

- CPI contais the consumer price index, from the US Bureau of Labor Statistics. It is used to translate the riskfree rate into real terms.


--------------------------------------


CODES

Files: table1.prg, table2.prg, tableA1.prg, and tableA2.prg

Each code corresponds to a table in the paper as the file's name indicates.
Each code is self-contained. They only need to read the data and the Gauss library "optmum".

We implement each SDF or regression method by continuously updated (CU), iterated and two-step (2S) GMM.
Each one of the three variants is associated to one of the three columns in each table.
The parameter "n_iter" at the beginning of the code controls which variant to run: 1 for CU-GMM, 2 for 2S-GMM, more for iterated GMM.
Once a value of "n_iter" is chosen, the code can be run and all the numbers of the corresponding column will be obtained.

The convergence of the estimates and the J statistic should be checked when running iterated GMM. 
To check the evolution of the estimates and the J statistic, simply delete @ in these parts of the code:  

@
    "--------------";
    "iteration" i ;
    "j, retcode and theta1'"; x[1,.];
@

In the output of the two symmetric normalizations, we report an equivalent angle below the estimate in case its value is outside (-pi/2,+pi/2).


--------------------------------------


EXAMPLE

This file is the output from running file "table1" with n_iter=1, which yields the first column of Table 1 in the paper.



