@table A2 - ccapm with gross return@
new;
cls ; 

@number of gmm iterations - 1 for cu-gmm, 2 for 2s-gmm, more for iterated gmm (check convergence)@
n_iter=1;


@----------------------------------@


library optmum ;
#include optmum.ext ;
optset;

rndseed(1) ; 


@----------------------------------@


@data: 1953-2002 - 50 obs.@

        @8 portfolios@
load y[50,9] = c:\pack\LV_port.txt  ;

        @2 factors  - Rvwexc and Consumption Growth@
load x[50,3] = c:\pack\LV_fac.txt  ;

d=y[.,1];


@--------------@
    
    @data: 52-10 - 59 obs. - date  MMR SMB HML RF@
load fama[59,5] = c:\pack\FF3a.txt  ;
    @sa 53-02@
sa=fama[2:51,5];

@cpi not seasonally adjusted: monthly 01/52-12/10 - 708 obs.@
load bls[708,3] = c:\pack\CPI.txt  ;
cpi=bls[.,3];

    @collecting december 52-02, then computing annual growth 53-02@
cpa={};
i=12; do while i<=612;
    cpa=cpa|cpi[i];    
i=i+12; endo;
cpa=100*(cpa[2:rows(cpa)]-cpa[1:rows(cpa)-1])./cpa[1:rows(cpa)-1];

sar=(1+sa/100)./(1+cpa/100);

@--------------@

@select r and f, and gross - per one@

r=(y[.,2:9]/100);
f=x[.,3]/100;
gr=sar;

@lags in newey-west @
lag_nw= 0  ; 
@center or not NW -  1 or 0@
cen_nw=1 ;

@optmum globals@
_opmiter=1000 ;
__output=0;
_opgtol = 1e-5 ;

@number of initial conditions and perturbation@
n_ic=10 ;
per_ic=0.1 ;
       

@----------------------------------@


n=cols(r);
k=cols(f);

t=rows(r);

df=n-k ; 

@------@


    @constructing the n-w matrix: newe(h,lag_nw)=h'nw_mat*h @
nw_mat=zeros(t,t);

i=1; do while i<=t;
    j=1; do while j<=t;
        nw_mat[i,j]=(lag_nw+1-abs(j-i))/(lag_nw+1)*(lag_nw+1-abs(j-i)>0) ;
    j=j+1; endo;
i=i+1; endo;

nw_mat=nw_mat/t ;

    @nw_mat=nw_sr'nw_sr@
nw_sr=chol(nw_mat) ;
nw_sri=inv(nw_sr) ; 


"-------------------------------------------------------------------" ; 

"uncentred sdf method" ;

w=eye(n+1) ;
theta0={1,1};

i=1; do while i<=n_iter; 

    x={};
    
    i2=1; do while i2<=n_ic;
      
        theta00=theta0+per_ic*rndn(rows(theta0),1);
        {theta1,fmin,g,retcode}=optmum(&sdf,theta00) ; 
        j=t*fmin;
    
        x=x|(j~retcode~theta1');

    i2=i2+1; endo;

    x=sortc(x,1);
    j=x[1,1]; 
    retcode=x[1,2];
    theta1=x[1,3:cols(x)]';

@
    "--------------";
    "iteration" i ;
    "j, retcode and theta1'"; x[1,.];
@

    if (n_iter>1)*(i==n_iter);

        d=gradp(&sdf_hm,theta1);
        avar=invpd(d'w*d);

        "--------------";
        "a&b estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "--------------";
    endif;

    
    
    s= newe(sdf_h(theta1),lag_nw);
    w=invpd( s ) ; 
    theta0=theta1;

    if n_iter==1;

        x={};

        i2=1; do while i2<=n_ic;

            theta00=theta0+per_ic*rndn(rows(theta0),1);
            {theta1,fmin,g,retcode}=optmum(&sdf_cu,theta00) ;  
            j=t*fmin ;

            x=x|(j~retcode~theta1');

        i2=i2+1; endo;

        x=sortc(x,1);
        j=x[1,1]; 
        retcode=x[1,2];
        theta1=x[1,3:cols(x)]';

        d=gradp(&sdf_hm,theta1);
        s=newe(sdf_h(theta1),lag_nw);
        si=invpd(s);

        ds=d-0.5*(sdf_hm(theta1)'si.*.eye(rows(d)))*gradp(&sdf_s,theta1);
        avar=inv(ds'si*ds);

        "---------------";
        "a&b estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "---------------";

        @for use in cu tests of problematic cases@
        theta1_a=theta1;
        j_a=j;

    endif;


i=i+1; endo;


"-------------------------------------------------------------------" ; 

"centred sdf method" ;

w=eye(n+1+k) ;
theta0={1,1};
theta0=theta0|meanc(f) ;

i=1; do while i<=n_iter;    

    x={};
    
    i2=1; do while i2<=n_ic;

        theta00=theta0+per_ic*rndn(rows(theta0),1);
        {theta1,fmin,g,retcode}=optmum(&sdf2,theta00) ; 
        j=t*fmin;
    
        x=x|(j~retcode~theta1');

    i2=i2+1; endo;

    x=sortc(x,1);
    j=x[1,1]; 
    retcode=x[1,2];
    theta1=x[1,3:cols(x)]';

@
    "--------------";
    "iteration" i ;
    "j, retcode and theta1'"; x[1,.];
@

    if (n_iter>1)*(i==n_iter);

        d=gradp(&sdf_hm2,theta1);
        avar=invpd(d'w*d);

        "--------------";
        "c&b and mu estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "--------------";

    endif;
    
    s= newe(sdf_h2(theta1),lag_nw);
    w=invpd( s ) ; 
    theta0=theta1;

    if n_iter==1;

        x={};

        i2=1; do while i2<=n_ic;

            theta00=theta0+per_ic*rndn(rows(theta0),1);
            {theta1,fmin,g,retcode}=optmum(&sdf_cu2,theta00) ;  
            j=t*fmin ;

            x=x|(j~retcode~theta1');

        i2=i2+1; endo;

        x=sortc(x,1);
        j=x[1,1]; 
        retcode=x[1,2];
        theta1=x[1,3:cols(x)]';

        d=gradp(&sdf_hm2,theta1);
        s=newe(sdf_h2(theta1),lag_nw);
        si=invpd(s);

        ds=d-0.5*(sdf_hm2(theta1)'si.*.eye(rows(d)))*gradp(&sdf_s2,theta1);
        avar=inv(ds'si*ds);

        "---------------";
        "c&b and mu estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "---------------";

    endif;


i=i+1; endo;


"-------------------------------------------------------------------" ; 

"centred regression" ;

w=eye((1+k)*(n+1)+k) ;
theta0=1|zeros(n+1,1)|meanc(f)|1 ;

i=1; do while i<=n_iter; 

    x={};
    
    i2=1; do while i2<=n_ic;

        theta00=theta0+per_ic*rndn(rows(theta0),1);
        {theta1,fmin,g,retcode}=optmum(&reg,theta00) ; 
        j=t*fmin;
    
        x=x|(j~retcode~theta1');

    i2=i2+1; endo;

    x=sortc(x,1);
    j=x[1,1]; 
    retcode=x[1,2];
    theta1=x[1,3:cols(x)]';

@
    "--------------";
    "iteration" i ;
    "j, retcode and theta1'"; x[1,.];
@


    if (n_iter>1)*(i==n_iter);

        d=gradp(&reg_hm,theta1);
        avar=invpd(d'w*d);

        "--------------";
        "lambda, betas, mu and varkappa; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "--------------";

    endif;

    s= newe(reg_h(theta1),lag_nw);
    w=invpd( s ) ; 
    theta0=theta1;

    if n_iter==1;

        x={};

        i2=1; do while i2<=n_ic;

            theta00=theta0+per_ic*rndn(rows(theta0),1);
            {theta1,fmin,g,retcode}=optmum(&reg_cu,theta00) ;  
            j=t*fmin ;

            x=x|(j~retcode~theta1');

        i2=i2+1; endo;

        x=sortc(x,1);
        j=x[1,1]; 
        retcode=x[1,2];
        theta1=x[1,3:cols(x)]';

        d=gradp(&reg_hm,theta1);
        s=newe(reg_h(theta1),lag_nw);
        si=invpd(s);

        ds=d-0.5*(reg_hm(theta1)'si.*.eye(rows(d)))*gradp(&reg_s,theta1);
        avar=inv(ds'si*ds);

        "---------------";
        "lambda, betas, mu and varkappa; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "---------------";

    endif;

i=i+1; endo;



@--------------------------------------------------------proc-----------------------------------------------------------------------@


proc  newe ( h , q ) ;

	local  u, t,  i , s, c ;

	t=rows(h) ;

    u=h-(cen_nw.==1)* meanc(h)' ;
	s=u'u / t ;  

	i=1 ; do while i<=q ; 
		c=u[i+1:t,.]'u[1:t-i,.]  / t  ; 
		s=s+ (1-(i/(q+1))) *  (  c+c' ) ; 
	i=i+1 ; endo ; 

	retp( s ) ;
endp; 

@--------------------------------@


proc  sdf_h ( theta ) ;

	local ab,  h_r_t, h_g_t  ;

    ab=theta;

    h_r_t= r.*(ab[1]+f*ab[2:rows(ab)]) ; 
    h_g_t= gr.*(ab[1]+f*ab[2:rows(ab)])-1 ; 

	   retp( h_r_t~h_g_t  ) ;
endp; 


proc  sdf_h2 ( theta ) ;

	local  cb, mu, u, h_r_t, h_u_t , h_g_t ;

    cb=theta[1:k+1];
    mu=theta[k+2:rows(theta)];

    u=f-mu';
    h_r_t= r.*(cb[1]+u*cb[2:rows(cb)]) ; 
    h_u_t= u ;
    h_g_t= gr.*(cb[1]+u*cb[2:rows(cb)])-1 ; 
   
	   retp( h_r_t~h_u_t~h_g_t ) ;
endp;


proc  reg_h ( theta ) ;

	local   lambda, beta, mu, vark,  bb ,h_r_t, h_u_t  ;

    lambda=theta[1:k];
    beta=theta[k+1:k+k*(n+1)];
    mu=theta[k+k*(n+1)+1:rows(theta)-1];
    vark=theta[rows(theta)];

    bb=reshape(beta,k,n+1)';

    h_r_t=(ones(t,1)~f) *~ ((r~(gr-vark))-(f-mu'+lambda')*bb') ;
    h_u_t= f -mu'; ; 
 
	retp( h_r_t~h_u_t ) ;

endp; 




@--------------------------------@



proc  sdf ( theta ) ;

	local  h  ;

    h=meanc(sdf_h(theta)) ; 

	retp( h'w*h  ) ;

endp; 


proc  sdf2 ( theta ) ;

	local  h  ;

    h=meanc(sdf_h2(theta)) ; 

	retp( h'w*h  ) ;
endp; 



proc  reg ( theta ) ;

	local    h ;
    
    h= meanc(reg_h(theta)) ; 

	retp( h'w*h ) ;

endp; 



@--------------------------------@


proc  sdf_hm ( theta ) ;

	retp( meanc(sdf_h(theta))  ) ;

endp; 

proc  sdf_s ( theta ) ;

	retp( vec(newe(sdf_h(theta),lag_nw))  ) ;

endp; 


proc  sdf_hm2 ( theta ) ;

	retp( meanc(sdf_h2(theta))  ) ;
endp; 

proc  sdf_s2 ( theta ) ;

	retp( vec(newe(sdf_h2(theta),lag_nw))  ) ;

endp; 



proc  reg_hm ( theta ) ;

	retp( meanc(reg_h(theta)) ) ;

endp; 

proc  reg_s ( theta ) ;

	retp( vec(newe(reg_h(theta),lag_nw))  ) ;

endp; 



@--------------------------------@



proc  sdf_cu ( theta ) ;

	local  h_t  ;

    h_t=sdf_h(theta) ; 

	retp( ols_r2(h_t)  ) ;
endp; 


proc  sdf_cu2 ( theta ) ;

	local  h_t  ;

    h_t=sdf_h2(theta) ; 

	retp( ols_r2(h_t)  ) ;
endp; 



proc  reg_cu ( theta ) ;

	local    h_t ;
    
    h_t= reg_h(theta) ; 

	retp( ols_r2(h_t) ) ;

endp; 




proc  ols_r2 ( mom ) ;

    local  alpha1,res1,pre1, c,fu,  alpha2,res2,pre2, kma,b ;

        { alpha1,res1,pre1 } = OLSQR2(nw_sri'ones(t,1),nw_sr*mom)   ;

        c=pre1'pre1/(t^2) ;

        fu=c;

        if cen_nw==1 ;

            { alpha2,res2,pre2 } = OLSQR2(nw_sr*ones(t,1),nw_sr*mom)   ;

            kma=res2'res2 ;
            b=-pre1'pre2/t  ;

            fu=c/(kma*c+(1+b)^2) ;
    
        endif;

    retp( fu ) ;

endp; 

