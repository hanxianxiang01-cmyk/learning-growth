(() => {
  const React=window.__vendor.r, ReactDOM=window.__vendor.e;
  const cache={}; const nativeJsx=window.__vendor.j;
  const assets=window.__assets||{};
  const propsFor=(type,props)=>type==='img'&&assets[props?.src]?{...props,src:assets[props.src]}:props;
  const jsx={...nativeJsx,jsx:(type,props,key)=>nativeJsx.jsx(type,propsFor(type,props),key),jsxs:(type,props,key)=>nativeJsx.jsxs(type,propsFor(type,props),key)};
  const router={push:href=>window.__navigate(href),replace:href=>window.__navigate(href),back:()=>window.__navigate('/child/math'),refresh:()=>window.__navigate(window.__route)};
  const normalize=s=>{const out=[];for(const bit of s.split('/')){if(bit==='..')out.pop();else if(bit&&bit!=='.')out.push(bit);}return out.join('/')};
  function load(id){
    id=normalize(id);
    const actual=[id,id+'.ts',id+'.tsx',id+'.json',id+'/index.ts',id+'/index.tsx'].find(x=>Object.hasOwn(window.__modules,x));
    if(!actual)throw new Error('Missing source module '+id);
    if(cache[actual])return cache[actual].exports;
    const mod={exports:{}};cache[actual]=mod;
    const req=spec=>{
      if(spec==='react')return React;
      if(spec==='react/jsx-runtime')return jsx;
      if(spec==='next/navigation')return {useRouter:()=>router,usePathname:()=>new URL(window.__route,'http://v6.test').pathname,useSearchParams:()=>new URL(window.__route,'http://v6.test').searchParams,notFound:()=>{throw new Error('404')},redirect:router.push};
      if(spec==='next/link')return ({href,children,...p})=>React.createElement('a',{...p,href,onClick:e=>{e.preventDefault();router.push(href)}},children);
      return load(spec.startsWith('@/')?spec.slice(2):normalize(actual.split('/').slice(0,-1).join('/')+'/'+spec));
    };
    const process={env:{NODE_ENV:'development',NEXT_PUBLIC_CHILD_UI_VERSION:'v6',NEXT_PUBLIC_LEARNING_API_MODE:'http',NEXT_PUBLIC_LEARNING_API_BASE_URL:'http://api.test'}};
    new Function('require','module','exports','process',window.__modules[actual]+'\n//# sourceURL=source://'+actual)(req,mod,mod.exports,process);
    return mod.exports;
  }
  window.__load=load;
  // Fail closed: this harness cannot send any real backend or external request.
  window.__apiCalls=[];
  window.fetch=async(input,init)=>{
    const url=typeof input==='string'?input:input.url;
    if(url.startsWith('http://api.test')){
      const call={url,method:init?.method||'GET',body:init?.body?JSON.parse(init.body):null};window.__apiCalls.push(call);
      if(!window.__apiHandler)throw new Error('No explicit API fixture installed');
      const reply=await window.__apiHandler(call);
      return new Response(JSON.stringify(reply.body),{status:reply.status??200,headers:{'Content-Type':'application/json'}});
    }
    throw new Error("Blocked non-fixture request: "+url);
  };
  const Provider=load('src/theme/ChildSkinProvider').ChildSkinProvider;
  const Gallery=load('src/dev/v6/V6Gallery').V6Gallery;
  const Home=load('src/screens/MathHomeScreen').MathHomeScreen;
  const Growth=load('src/screens/MathGrowthScreen').MathGrowthScreen;
  const Result=load('src/screens/MathResultScreen').MathResultScreen;
  const Learning=load('src/screens/MathLearningScreen').MathLearningScreen;
  function Root(){
    const [href,setHref]=React.useState(window.__initialPath||'/dev/v6');
    const [skin,setSkin]=React.useState('exploration-lab');
    window.__navigate=next=>{window.__route=next;setHref(next)};window.__setSkin=setSkin;window.__route=href;
    const url=new URL(href,'http://v6.test');
    const childId=url.searchParams.get('child_id')||'00000000-0000-0000-0000-000000000099';
    const props={childId};const parts=url.pathname.split('/');
    const screen=url.pathname.includes('/dev/')?React.createElement(Gallery):url.pathname.includes('/growth')?React.createElement(Growth,props):url.pathname.includes('/result/')?React.createElement(Result,{...props,sessionId:parts[4]}):url.pathname.includes('/session/')?React.createElement(Learning,{...props,sessionId:parts[4],abilityId:url.searchParams.get('ability_id')||undefined}):React.createElement(Home,props);
    return React.createElement(Provider,{skin,uiVersion:'v6'},screen);
  }
  document.addEventListener('click',event=>{const a=event.target.closest?.('a[href]');if(a&&a.getAttribute('href').startsWith('/child/')){event.preventDefault();window.__navigate(a.getAttribute('href'));}});
  window.__root=ReactDOM.createRoot(document.getElementById('root'));
  window.__root.render(React.createElement(Root));
  window.__harnessMeta={react:React.version,reactDOM:ReactDOM.version,scope:'isolated real components; substituted Next navigation, inlined local SVG and fixture fetch; NOT a Next build or live backend test'};
})();
