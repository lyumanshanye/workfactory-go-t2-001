@table A1 - epstein-zin@
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

@select r and f - epstein-zin@

r=y[.,2:9];
f=x[.,2];
fno=x[.,3];

r=r/100;
f=f/100;
fno=fno/100;

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
kno=cols(fno);

nn=n+k;
kk=k+kno;

t=rows(r);

df=n-kno ; 

rr=r~f;
ff=f~fno;

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

"uncentred sdf method - symmetric normalization" ;

w=eye(nn) ;
theta0=zeros(2,1);

i=1; do while i<=n_iter; 

    x={};
    
    i2=1; do while i2<=n_ic;
      
        theta00=theta0+per_ic*rndn(rows(theta0),1);
        {theta1,fmin,g,retcode}=optmum(&sdfp,theta00) ; 
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

        d=gradp(&sdf_hmp,theta1);
        avar=invpd(d'w*d);

        "--------------";
        "psi 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "equivalent psi in case value above is outside (-pi/2,+pi/2)"; psi=theta1; atan(sin(psi)./cos(psi))';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "--------------";
    endif;
    
    
    s= newe(sdf_hp(theta1),lag_nw);
    w=invpd( s ) ; 
    theta0=theta1;

    if n_iter==1;

        x={};

        i2=1; do while i2<=n_ic;

            theta00=theta0+per_ic*rndn(rows(theta0),1);
            {theta1,fmin,g,retcode}=optmum(&sdf_cup,theta00) ;  
            j=t*fmin ;

            x=x|(j~retcode~theta1');

        i2=i2+1; endo;

        x=sortc(x,1);
        j=x[1,1]; 
        retcode=x[1,2];
        theta1=x[1,3:cols(x)]';

        d=gradp(&sdf_hmp,theta1);
        s=newe(sdf_hp(theta1),lag_nw);
        si=invpd(s);

        ds=d-0.5*(sdf_hmp(theta1)'si.*.eye(rows(d)))*gradp(&sdf_sp,theta1);
        avar=inv(ds'si*ds);

        "---------------";
        "psi 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "equivalent psi in case value above is outside (-pi/2,+pi/2)"; psi=theta1; atan(sin(psi)./cos(psi))';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "---------------";

    endif;


i=i+1; endo;


"-------------------------------------------------------------------" ; 

"centred sdf method - symmetric normalization" ;

w=eye(nn+kk) ;
theta0=zeros(2,1)|meanc(ff) ;

i=1; do while i<=n_iter;    

    x={};
    
    i2=1; do while i2<=n_ic;

        theta00=theta0+per_ic*rndn(rows(theta0),1);
        {theta1,fmin,g,retcode}=optmum(&sdf2p,theta00) ; 
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

        d=gradp(&sdf_hm2p,theta1);
        avar=invpd(d'w*d);

        "--------------";
        "upsilon 1&2 and mu 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "equivalent upsilon in case value above is outside (-pi/2,+pi/2)"; ups=theta1[1:2]; atan(sin(ups)./cos(ups))';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "--------------";

    endif;
    
    s= newe(sdf_h2p(theta1),lag_nw);
    w=invpd( s ) ; 
    theta0=theta1;

    if n_iter==1;

        x={};

        i2=1; do while i2<=n_ic;

            theta00=theta0+per_ic*rndn(rows(theta0),1);
            {theta1,fmin,g,retcode}=optmum(&sdf_cu2p,theta00) ;  
            j=t*fmin ;

            x=x|(j~retcode~theta1');

        i2=i2+1; endo;

        x=sortc(x,1);
        j=x[1,1]; 
        retcode=x[1,2];
        theta1=x[1,3:cols(x)]';

        d=gradp(&sdf_hm2p,theta1);
        s=newe(sdf_h2p(theta1),lag_nw);
        si=invpd(s);

        ds=d-0.5*(sdf_hm2p(theta1)'si.*.eye(rows(d)))*gradp(&sdf_s2p,theta1);
        avar=inv(ds'si*ds);

        "---------------";
        "upsilon 1&2 and mu 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "equivalent upsilon in case value above is outside (-pi/2,+pi/2)"; ups=theta1[1:2]; atan(sin(ups)./cos(ups))';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "---------------";

    endif;


i=i+1; endo;


"-------------------------------------------------------------------" ; 

"uncentred sdf method - asymmetric normalization" ;

w=eye(nn) ;
theta0=ones(2,1);

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
        "delta 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
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
        "delta 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "---------------";

        @for use in cu tests of problematic cases@
        theta1_a=theta1;
        j_a=j;

    endif;


i=i+1; endo;


"-------------------------------------------------------------------" ; 

"centred sdf method - asymmetric normalization" ;

w=eye(nn+kk) ;
theta0=ones(2,1)|meanc(ff) ;

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
        "tau 1&2 and mu 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
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
        "tau 1&2 and mu 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
        "j statistic, p-value, and optmum retcode" ; j~cdfchic(j,df)~retcode ;
        "---------------";

    endif;


i=i+1; endo;


"-------------------------------------------------------------------" ; 

"centred regression - asymmetric normalization" ;

w=eye((1+kk)*n+kk) ;
theta0=0|zeros(2*n,1)|meanc(ff) ;

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
        "lambda, betas and mu 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
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
        "lambda, betas and mu 1&2 estimates; standard error below"; theta1' ; sqrt(diag(avar)/t)';
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

proc  sdf_hp ( theta ) ;

       local psi1, psi2, m ;

    psi1=theta[1];
    psi2=theta[2];
    m=sin(psi1)+f*cos(psi1)*sin(psi2)+fno*cos(psi1)*cos(psi2) ;

    retp( rr.*m ) ;

endp; 

proc  sdf_h2p ( theta ) ;

	local   ups1, ups2,  mu, u, m ;

    ups1=theta[1];
    ups2=theta[2];
    mu=theta[3:4]; 
    u=ff-mu';
    m=sin(ups1)+u[.,1]*cos(ups1)*sin(ups2)+u[.,2]*cos(ups1)*cos(ups2) ;

	   retp( (rr.*m) ~ u  ) ;
endp; 


proc  sdf_h ( theta ) ;

	local   h_r_t, h_f_t ;

    h_r_t= r.*(1-ff*theta) ; 
    h_f_t= f.*(1-ff*theta) ;
   
	   retp( h_r_t~h_f_t  ) ;
endp; 


proc  sdf_h2 ( theta ) ;

	local  tau, mu, 
            u, h_r_t, h_f_t, h_u_t ;

    tau=theta[1:kk];
    mu=theta[kk+1:2*kk];

    u=ff-mu';
    h_r_t= r.*(1-u*tau) ; 
    h_f_t= f.*(1-u*tau) ;
    h_u_t= u ;

  	   retp(h_r_t~h_f_t~h_u_t );
endp;


proc  reg_h ( theta ) ;


	local   lamno, beta, mu,  bb ;

    lamno=theta[1:kno];
    beta=theta[kno+1:kno+kk*n];
    mu=theta[kno+kk*n+1:rows(theta)];

    bb=reshape(beta,kk,n)';
 
	retp( ((ones(t,1)~ff) *~ (r-f*bb[.,1:k]'-(fno-mu[k+1:rows(mu)]'+lamno')*bb[.,k+1:cols(bb)]')) ~ (ff-mu') ) ;

endp; 



@--------------------------------@

proc  sdfp ( theta ) ;

	local  h  ;

    h=meanc(sdf_hp(theta)) ; 

	retp( h'w*h  ) ;

endp; 


proc  sdf2p ( theta ) ;

	local  h  ;

    h=meanc(sdf_h2p(theta)) ; 

	retp( h'w*h  ) ;
endp; 



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

proc  sdf_hmp ( theta ) ;

	retp( meanc(sdf_hp(theta))  ) ;

endp; 

proc  sdf_sp ( theta ) ;

	retp( vec(newe(sdf_hp(theta),lag_nw))  ) ;

endp; 


proc  sdf_hm2p ( theta ) ;

	retp( meanc(sdf_h2p(theta))  ) ;
endp; 

proc  sdf_s2p ( theta ) ;

	retp( vec(newe(sdf_h2p(theta),lag_nw))  ) ;

endp; 



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

proc  sdf_cup ( theta ) ;

	local  h_t  ;

    h_t=sdf_hp(theta) ; 

	retp( ols_r2(h_t)  ) ;
endp; 


proc  sdf_cu2p ( theta ) ;

	local  h_t  ;

    h_t=sdf_h2p(theta) ; 

	retp( ols_r2(h_t)  ) ;
endp; 



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

