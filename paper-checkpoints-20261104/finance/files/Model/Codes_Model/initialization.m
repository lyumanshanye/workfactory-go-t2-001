function  par =  initialization( par_input )
% Key Points: if par_input is not given, then initialize the parameters as a rational model, par.model_name has three values:  'benchmark', 'rational', and 'behavioral'.
% If par_input is given, then we should use the crisis frequency from par_input.  

if(nargin<1)  % No input. Then just set the model as a rational model, and crisis target as the 12.2%
    par.model_name = 'rational';   % default is the rational model
    % (0) Credit spread
    par.crisis_frequency_target = 0.122;
    par.bond_default_probability =  0.04;
    par.loss_given_default = 0.55;  % Loss given default is 55%
    par.hat_kappa0 = par.loss_given_default - 0.06;   % note: the 6% is the average price decline of capital during a crisis.  This one will be adjusted after the model is solved.
    par.tau = 7;   % 7 years
    par.pi = par.bond_default_probability/(par.crisis_frequency_target);
    
    par.alg_control.plot = false;    par.alg_control.show_progress=false;   par.alg_control.solve_everything_again=false;
    
    % (1) Key parameters related to bank run and beliefs
    alpha = 0.05;  beta=1; 
    % Parameter trials: alpha=0.1, beta=0.1 is too low that results in negligible declines in productivity. 
    lambda_L=0.001;  lambda_H = 0.5;
    lambdaHL=0.5; 
    lambdaLH = fzero( @(lambdaLH)   lambdaLH / (lambdaLH+lambdaHL) * lambda_H  + lambdaHL / (lambdaLH+lambdaHL) * lambda_L - par.crisis_frequency_target,  0.15  );    

    % diagnostic belief parameters
    theta_diagnostic = 0.9; 
    lag_years = 1; 

    % (2) Other parameters
    AL=0.12;  AH=0.15; 
    rho = 0.04;  sigmaK=0.04;  delta=0.1;    chi=3;
    eta=0.03; 
    e = 0.001;  varepsilon=0.00001;  % Bank Run parameters.
    par.HQ_Cutoff=0.03;
else
    par = par_input;
    if( ~isfield(par, 'loss_given_default' ) )
        par.loss_given_default = 0.55;  
    end
    % (1) Key parameters related to bank run and beliefs
    alpha = par_input.alpha;  beta=par_input.beta; 
    % Parameter trials: alpha=0.1, beta=0.1 is too low that results in negligible declines in productivity. 
    lambda_L=par_input.lambda_L;  lambda_H = par_input.lambda_H;
    lambdaHL= par_input.lambdaHL;  lambdaLH=par_input.lambdaLH; 
    % diagnostic belief parameters
    theta_diagnostic = par_input.theta_diagnostic; 
    lag_years = par_input.lag_years; 

    % (2) Other parameters
    AL=par_input.AL;  AH=par_input.AH; 
    rho = par_input.rho;  sigmaK=par_input.sigmaK;  delta=par_input.delta;    chi=par_input.chi;
    eta=par_input.eta; 
    e = par_input.e;  varepsilon=par_input.varepsilon;  % Bank Run parameters.
    par.HQ_Cutoff = par_input.HQ_Cutoff;
    
    if(isfield(par_input, 'model_name'))    
        par.model_name = par_input.model_name;
    else   % If there is not a model name field, then treat this model as a rational model.
        par.model_name = 'rational';   
    end
    % if( strncmp(par_input.model_name, 'benchmark',20) )  % if this is for the benchmark model without belief variation, set the belief as the average belief in the rational case. 
    %     epsilon = 0.001;
    %     lambda_L =  par_input.lambda_H*(1-epsilon);
    %     lambda_H =  par_input.lambda_H;
    %     lambdaHL= 0.5;  lambdaLH=0.1;  % note: the underlying intensity is always the same. However, lambda_H is what drives the frequency of the liquidity shock. This facilitates model calibration.
    % end
    par.pi = par_input.bond_default_probability/(par_input.tau*par_input.crisis_frequency_target);  % Update the pi according to the default probability in par_input.
end
 
% (3) Functions
muK_fun = @(p) (p-1)/chi  + delta;   % This is the amount of actual "investment"
investment =  @(p)  (p-1).^2/(2*chi) + (p-1)./chi + delta ;    %  This is the investment adjustment cost, or the real resources consumed.
investmentD = @(p)  p/chi ; 
%  Jump 
kappa_lambda_fun = @(lambda)  (lambda - lambda_L).*(lambda_H-lambda)./lambda;    % Jump in lambda
mu_lambda_fun = @(lambda) (lambda_L - lambda).*lambdaHL  + (lambda_H - lambda).*lambdaLH - (lambda-lambda_L).*(lambda_H-lambda);  % Drift in lambda

% (3) Limit values
p0 = fsolve(  @(p)  investment(p) + rho*p - AL,  1 ,   optimoptions( 'fsolve','Display','none' ) );  % The initial condition
p1 = fsolve(  @(p)  investment(p) + rho*p - AH,  1 ,   optimoptions( 'fsolve','Display','none' ) );  % The end value at w=1, or psi=1

% (4) Record parameters for call-back inside functions.   par is a struct that includes all the relevant parameters for other functions
par.AH  = AH;  par.AL  = AL;  par.rho  = rho;  par.sigmaK  = sigmaK;   
par.max_jump = 0.5; par.delta = delta;   par.eta=eta;   
par.alpha = alpha;  par.beta=beta;
par.lambda_H = lambda_H; par.lambda_L = lambda_L;    par.lambdaHL=lambdaHL; par.lambdaLH=lambdaLH; 
par.theta_diagnostic = theta_diagnostic;     par.lag_years = lag_years; 
par.kappa_lambda_fun =kappa_lambda_fun;    par.mu_lambda_fun = mu_lambda_fun;
par.investment=investment;   par.investmentD=investmentD;   
par.muK_fun = muK_fun;   
par.chi = chi;
par.p0 = p0; par.p1=p1;  
par.e = e;  par.varepsilon = varepsilon;

% (4)  Grid
N_w    = 60;    
N_lambda = 10;
lambda_grid = [ exp( linspace( log(lambda_L+0.001), log( max(lambda_H/5,lambda_L*0.9+0.1*lambda_H) ) ,  5 )')-0.001 ;  linspace( max(lambda_H/5*2,lambda_L*0.9+0.1*lambda_H), lambda_H,  N_lambda-5 )'  ];  
w_left = [ 0 ;  exp( linspace(log(0.001), log(0.4),  round(N_w/4*3) )'  )  ] ;
w_star = max(w_left);   w_rest = linspace( w_star+ w_left(end)-w_left(end-1) , 1,  N_w - numel(w_left)  )';   
w_grid = [w_left; w_rest ];     
w_matrix = kron(  w_grid,   ones( 1, N_lambda )   );
lambda_matrix = kron(  ones( N_w, 1 ),   lambda_grid'   );

% (6) Record the grid and algorithm control information
par.w_grid = w_grid;  par.lambda_grid = lambda_grid;
par.N_w    =  N_w;   par.N_lambda = N_lambda;
par.w_matrix = w_matrix; par.lambda_matrix = lambda_matrix;
dt = 1/12;    par.dt = dt;    % The time interval for simulation
par.tol = 0.8*10^(-3);   % The tolerance for iteration errors in the 2D case.
par.print_level = 0;


