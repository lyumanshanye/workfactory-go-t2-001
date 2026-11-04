function    irr_lambda = irrational_lambda(  lambda,  lambda_reference, lag_years, parameters  )
%   USAGE:   irrational_lambda(  lambda,  lambda_reference, lag_years, parameters  )
%
%   lambda and lambda_reference can be both vectors of the same length.    The diagnostic belief is using
%   lambda_reference as the reference point, and then distor the distribution on lambda.
%   lag_years specifies the look-back years for diagnostic expectation. 

theta_diagnostic = parameters.theta_diagnostic;
lambda_H = parameters.lambda_H;
lambda_L = parameters.lambda_L;

a = parameters.lambdaHL; 
b = parameters.lambdaLH;
aH = (b+a*exp(-(a+b)*lag_years)) / (a+b); 
bH = 1-aH;  
aL = (b-b*exp(-(a+b)*lag_years)) / (a+b); 
bL = 1 - aL; 

lambdaT_lambdaL = aH*(lambda_reference-lambda_L) + aL*(lambda_H-lambda_reference);
lambdaH_lambdaT = bH*(lambda_reference-lambda_L) + bL*(lambda_H-lambda_reference);
ratio= (lambdaT_lambdaL./lambdaH_lambdaT) ./ ((lambda-lambda_L)./(lambda_H-lambda)) ;
irr_lambda = (lambda-lambda_L)  .*  (lambda_H-lambda_L)./( ratio.^theta_diagnostic.*(lambda_H-lambda) + (lambda-lambda_L) )  +  lambda_L;



