/* Offline, dependency-free glTF subset loader for this authored asset. */
'use strict';
(function(){
 const T=THREE, $=s=>document.querySelector(s), status=$('#status');
 window.addEventListener('error',e=>{const el=$('#error');el.classList.add('show');el.textContent='模型显示失败：'+e.message;});
 const bytes=Uint8Array.from(atob(VEHICLE_GLB),c=>c.charCodeAt(0)), dv=new DataView(bytes.buffer);
 if(dv.getUint32(0,true)!==0x46546c67)throw Error('Invalid vehicle GLB');
 const jlen=dv.getUint32(12,true), gltf=JSON.parse(new TextDecoder().decode(bytes.subarray(20,20+jlen))), bin=bytes.subarray(28+jlen);
 const types={5120:Int8Array,5121:Uint8Array,5122:Int16Array,5123:Uint16Array,5125:Uint32Array,5126:Float32Array}, sizes={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16};
 function accessor(idx){const a=gltf.accessors[idx],v=gltf.bufferViews[a.bufferView],C=types[a.componentType],n=sizes[a.type],start=(v.byteOffset||0)+(a.byteOffset||0),width=n*C.BYTES_PER_ELEMENT;
  if(a.sparse)throw Error('Unexpected sparse accessor');
  if(v.byteStride&&v.byteStride!==width){const out=new C(a.count*n);for(let i=0;i<a.count;i++)out.set(new C(bin.buffer.slice(bin.byteOffset+start+i*v.byteStride,bin.byteOffset+start+i*v.byteStride+width)),i*n);return out;}
  return new C(bin.buffer.slice(bin.byteOffset+start,bin.byteOffset+start+a.count*width));}
 const renderer=new T.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0,0);renderer.outputColorSpace=T.SRGBColorSpace;$('#stage').appendChild(renderer.domElement);
 const world=new T.Scene(), model=new T.Group();world.add(model);
 const camera=new T.OrthographicCamera(-8,8,5,-5,.1,100);let target=new T.Vector3(.5,1.5,0),yaw=.95,elev=.5,zoom=1;
 const vertex=`varying vec3 n; void main(){vec4 p=vec4(position,1.0);vec3 nn=normal;
 #ifdef USE_INSTANCING
 p=instanceMatrix*p;nn=mat3(instanceMatrix)*nn;
 #endif
 n=normalize(mat3(modelMatrix)*nn);gl_Position=projectionMatrix*modelViewMatrix*p;}`;
 const fragment=`varying vec3 n; uniform vec3 base;void main(){float light=dot(normalize(n),normalize(vec3(.28,.86,.43)));vec3 c=base*(.85+.12*light);float hatch=1.0-smoothstep(.07,.18,abs(sin((gl_FragCoord.x+gl_FragCoord.y*.68)*.60)));float shadow=1.0-smoothstep(.45,.75,light);c=mix(c,vec3(.24,.34,.46),hatch*shadow*.35);gl_FragColor=vec4(c,1.0);}`;
 const edgeMat=new T.LineBasicMaterial({color:0x203e60,transparent:true,opacity:.83});
 const outline=new T.ShaderMaterial({side:T.BackSide,vertexShader:`void main(){vec4 p=vec4(position+normal*.004,1.0);
 #ifdef USE_INSTANCING
 p=instanceMatrix*p;
 #endif
 gl_Position=projectionMatrix*modelViewMatrix*p;}`,fragmentShader:'void main(){gl_FragColor=vec4(.10,.19,.31,1.0);}'});
 const mats=(gltf.materials||[]).map(m=>new T.ShaderMaterial({vertexShader:vertex,fragmentShader:fragment,uniforms:{base:{value:new T.Vector3(...(m.pbrMetallicRoughness?.baseColorFactor||[.91,.94,.97]).slice(0,3))}},polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));
 const meshes=(gltf.meshes||[]).map(m=>m.primitives.map(p=>{const g=new T.BufferGeometry();g.setAttribute('position',new T.BufferAttribute(accessor(p.attributes.POSITION),3));if(p.attributes.NORMAL!==undefined)g.setAttribute('normal',new T.BufferAttribute(accessor(p.attributes.NORMAL),3));if(p.indices!==undefined)g.setIndex(new T.BufferAttribute(accessor(p.indices),1));if(!g.attributes.normal)g.computeVertexNormals();return {g,edges:new T.EdgesGeometry(g,30),mat:mats[p.material||0]};}));
 const nodes=gltf.nodes.map(n=>{const o=new T.Group();o.name=n.name||'';if(n.matrix)o.applyMatrix4(new T.Matrix4().fromArray(n.matrix));else{if(n.translation)o.position.fromArray(n.translation);if(n.rotation)o.quaternion.fromArray(n.rotation);if(n.scale)o.scale.fromArray(n.scale);}if(n.mesh!==undefined)for(const p of meshes[n.mesh]){o.add(new T.Mesh(p.g,p.mat));o.add(new T.LineSegments(p.edges,edgeMat));o.add(new T.Mesh(p.g,outline));}return o;});
 gltf.nodes.forEach((n,i)=>(n.children||[]).forEach(c=>nodes[i].add(nodes[c])));
 for(const n of gltf.scenes[gltf.scene||0].nodes)model.add(nodes[n]);
 const named={};nodes.forEach(o=>named[o.name]=o);
 const mixer=new T.AnimationMixer(model), allTracks=[];
 for(const anim of gltf.animations||[])for(const ch of anim.channels){const sa=anim.samplers[ch.sampler],times=accessor(sa.input),vals=accessor(sa.output),o=nodes[ch.target.node],prop=ch.target.path,Class=prop==='rotation'?T.QuaternionKeyframeTrack:T.VectorKeyframeTrack;allTracks.push(new Class(o.uuid+'.'+({rotation:'quaternion',translation:'position',scale:'scale'}[prop]),times,vals,sa.interpolation==='STEP'?T.InterpolateDiscrete:T.InterpolateLinear));}
 const clip=new T.AnimationClip('Inspection',-1,allTracks), action=mixer.clipAction(clip);action.play();mixer.setTime(0);
 const box=new T.Box3().setFromObject(model);box.getCenter(target);const radius=box.getSize(new T.Vector3()).length()*.5;
 // Keep animation nodes, while drawing repeated track geometry as shared instances.
 const trackNodes=nodes.filter(n=>n.name.includes('_LINK_')),instances=[];
 if(trackNodes.length){
  const firstIndex=nodes.indexOf(trackNodes[0]),prims=meshes[gltf.nodes[firstIndex].mesh];
  for(const n of trackNodes)while(n.children.length)n.remove(n.children[0]);
  for(const p of prims){
   const fill=new T.InstancedMesh(p.g,p.mat,trackNodes.length),silhouette=new T.InstancedMesh(p.g,outline,trackNodes.length);
   fill.frustumCulled=silhouette.frustumCulled=false;fill.instanceMatrix.setUsage(T.DynamicDrawUsage);silhouette.instanceMatrix.setUsage(T.DynamicDrawUsage);model.add(fill,silhouette);
   const eg=new T.InstancedBufferGeometry();eg.setAttribute('position',p.edges.getAttribute('position'));eg.instanceCount=trackNodes.length;
   const attrs=[];for(let c=0;c<4;c++){const a=new T.InstancedBufferAttribute(new Float32Array(trackNodes.length*4),4);a.setUsage(T.DynamicDrawUsage);attrs.push(a);eg.setAttribute('i'+c,a);}
   const lm=new T.ShaderMaterial({transparent:true,vertexShader:'attribute vec4 i0;attribute vec4 i1;attribute vec4 i2;attribute vec4 i3;void main(){gl_Position=projectionMatrix*viewMatrix*mat4(i0,i1,i2,i3)*vec4(position,1.0);}',fragmentShader:'void main(){gl_FragColor=vec4(.125,.243,.376,.83);}'});
   const lines=new T.LineSegments(eg,lm);lines.frustumCulled=false;model.add(lines);instances.push({fill,silhouette,attrs});
  }
 }
 function updateInstances(){for(const batch of instances){for(let i=0;i<trackNodes.length;i++){const m=trackNodes[i].matrixWorld;batch.fill.setMatrixAt(i,m);batch.silhouette.setMatrixAt(i,m);for(let c=0;c<4;c++)batch.attrs[c].setXYZW(i,m.elements[c*4],m.elements[c*4+1],m.elements[c*4+2],m.elements[c*4+3]);}batch.fill.instanceMatrix.needsUpdate=batch.silhouette.instanceMatrix.needsUpdate=true;batch.attrs.forEach(a=>a.needsUpdate=true);}}
 const grid=new T.GridHelper(20,40,0x8fa2b7,0xbbc8d6);grid.position.y=-.075;grid.material.transparent=true;grid.material.opacity=.32;world.add(grid);
 const shotFX=new FerdinandFireEffects(world),turretNode=named.TURRET_YAW_PIVOT;
 let aimYaw=0,aimElevation=0;
 let view='iso',motion='',lastMotion='',clock=0,exploded=0,wantExplode=0,last=performance.now(),paused=false;
 const ranges={drive:[1/30,61/30],aim:[81/30,170/30],fire:[181/30,208/30],hatches:[221/30,280/30],shoot:[301/30,385/30],rotate:[401/30,521/30]};
 const labels={drive:'履带循环',aim:'炮塔瞄准',rotate:'炮塔旋转',fire:'后坐复进',hatches:'舱盖开合',explode:'分解观察',shoot:'单次开火'};
 const states={iso:[10,9,12],rear_iso:[-10,8,12],side:[0,0,1],front:[1,0,0],rear:[-1,0,0],top:[0,1,.00001]};
 let baseScale=12, aspect=1,frameReserve=1;
 function updateCamera(){camera.up.set(0,1,0);camera.position.set(Math.cos(yaw)*Math.cos(elev),Math.sin(elev),Math.sin(yaw)*Math.cos(elev)).multiplyScalar(25).add(target);camera.lookAt(target);camera.updateMatrixWorld();camera.left=-baseScale*frameReserve*aspect/(2*zoom);camera.right=-camera.left;camera.top=baseScale*frameReserve/(2*zoom);camera.bottom=-camera.top;camera.updateProjectionMatrix();}
 function frameTurret(dt){const bounds=new T.Box3().setFromObject(turretNode);let need=1;for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z]){const p=new T.Vector3(x,y,z).applyMatrix4(camera.matrixWorldInverse);need=Math.max(need,Math.abs(p.x)*2.25/(baseScale*aspect),Math.abs(p.y)*2.45/baseScale);}const next=T.MathUtils.damp(frameReserve,need,8,dt);if(Math.abs(next-frameReserve)>.0001){frameReserve=next;updateCamera();}}
 function fit(){updateCamera();const ps=[];for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z])ps.push(new T.Vector3(x,y,z).applyMatrix4(camera.matrixWorldInverse));const dx=Math.max(...ps.map(v=>v.x))-Math.min(...ps.map(v=>v.x)),dy=Math.max(...ps.map(v=>v.y))-Math.min(...ps.map(v=>v.y));baseScale=Math.max(dx/aspect,dy)*1.31;updateCamera();}
 function setView(name){view=name;zoom=1;const d=new T.Vector3(...states[name]).normalize();yaw=Math.atan2(d.z,d.x);elev=Math.asin(d.y);elev=Math.min(1.57078,elev);fit();$('#views').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.view===name));}
 function resize(){const w=innerWidth,h=innerHeight;renderer.setSize(w,h);aspect=w/h;fit();}window.addEventListener('resize',resize);resize();setView('iso');
 const rest=new Map(nodes.map(n=>[n,n.position.clone()]));
 function separation(o){const n=o.name;if(n==='TURRET_YAW_PIVOT')return new T.Vector3(0,.85,0);if(n==='GUN_TRAVERSE_PIVOT')return new T.Vector3(.75,.25,0);if(n==='SUSPENSION_L'||n==='TRACKS_L')return new T.Vector3(0,0,.65);if(n==='SUSPENSION_R'||n==='TRACKS_R')return new T.Vector3(0,0,-.65);if(/^(FRONT_IDLER|REAR_SPROCKET)_[LR]$/.test(n))return new T.Vector3(0,0,n.endsWith('L')?.65:-.65);return new T.Vector3();}
 const separated=nodes.filter(n=>separation(n).length()>0);const cachedSep=new Map(separated.map(n=>[n,separation(n)]));
 function chooseMotion(name){
  if(name==='reset'){aimYaw=0;aimElevation=0;}
  clock=0;paused=false;wantExplode=0;motion=name==='reset'?'':name;lastMotion=ranges[name]?name:'';shotFX.clear();
  separated.forEach(n=>n.position.copy(rest.get(n)));exploded=0;named.GUN_TRAVERSE_PIVOT.quaternion.identity();mixer.setTime(0);applyManualAim();
  if(name==='shoot'){world.updateMatrixWorld(true);shotFX.capture(named.SOCKET_MUZZLE);}
  if(name==='explode'){motion='';wantExplode=1;}
  $('#actions').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.action===name&&name!=='reset'));$('#motion').textContent=labels[name]||'静止';$('#pause').textContent='暂停';$('#progress').value=0;
 }
 function applyManualAim(){turretNode.quaternion.setFromAxisAngle(new T.Vector3(0,1,0),T.MathUtils.degToRad(aimYaw));named.GUN_PITCH_PIVOT.quaternion.setFromAxisAngle(new T.Vector3(0,0,1),T.MathUtils.degToRad(aimElevation));}
 function applyMotion(){if(!ranges[motion])return;const r=ranges[motion],duration=r[1]-r[0];const t=(motion==='shoot'||paused)?Math.min(clock,duration):clock%duration;mixer.setTime(r[0]+t);if(motion==='aim'||motion==='rotate'){const forward=new T.Vector3(1,0,0).applyQuaternion(turretNode.quaternion);aimYaw=T.MathUtils.radToDeg(Math.atan2(-forward.z,forward.x));aimElevation=T.MathUtils.radToDeg(named.GUN_PITCH_PIVOT.rotation.z);}else applyManualAim();$('#progress').value=Math.round(t/duration*100);}
 $('#views').addEventListener('click',e=>{if(e.target.dataset.view)setView(e.target.dataset.view);});$('#actions').addEventListener('click',e=>{if(e.target.dataset.action)chooseMotion(e.target.dataset.action);});
 $('#pause').addEventListener('click',()=>{if(!lastMotion)return;paused=!paused;if(!paused&&motion==='shoot'&&clock>=2.8){chooseMotion('shoot');return;}$('#pause').textContent=paused?'播放':'暂停';});
 $('#progress').addEventListener('input',e=>{if(!lastMotion)return;motion=lastMotion;paused=true;clock=Number(e.target.value)/100*(ranges[motion][1]-ranges[motion][0]);$('#pause').textContent='播放';$('#motion').textContent=labels[motion]+' · 已暂停';applyMotion();world.updateMatrixWorld(true);updateInstances();if(motion==='shoot')shotFX.update(clock,named.SOCKET_MUZZLE);renderer.render(world,camera);updateReadouts();});
 window.addEventListener('keydown',e=>{if(e.code==='Space'&&!/INPUT|BUTTON/.test(e.target.tagName)){e.preventDefault();chooseMotion('shoot');}});
 for(const id of ['yaw-control','elevation-control'])$('#'+id).addEventListener('input',e=>{if(id==='yaw-control')aimYaw=Number(e.target.value);else aimElevation=Number(e.target.value);chooseMotion('manual');motion='';$('#motion').textContent='手动瞄准';applyManualAim();world.updateMatrixWorld(true);updateInstances();renderer.render(world,camera);updateReadouts();});
 let drag=null;renderer.domElement.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];renderer.domElement.setPointerCapture(e.pointerId);});renderer.domElement.addEventListener('pointerup',()=>drag=null);renderer.domElement.addEventListener('pointercancel',()=>drag=null);
 renderer.domElement.addEventListener('pointermove',e=>{if(!drag)return;view='custom';yaw+=(e.clientX-drag[0])*.006;elev=Math.max(-.05,Math.min(1.55,elev+(e.clientY-drag[1])*.005));drag=[e.clientX,e.clientY];updateCamera();$('#views').querySelectorAll('button').forEach(b=>b.classList.remove('active'));});
 renderer.domElement.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.5,Math.min(3,zoom*Math.exp(-e.deltaY*.001)));updateCamera();},{passive:false});
 const points=[[-1.52,2.5,1.43],[-.66,3.5,.77],[-2.28,4.35,-.91],[-1.65,2.44,1.48],[.445,.56,1.85],[-1.3,.05,1.79]];
 const markers=points.map((p,i)=>{const el=document.createElement('div');el.className='marker';el.textContent=i+1;$('#markers').appendChild(el);return {p:new T.Vector3(...p),el};});
 function updateReadouts(){$('#elevation').textContent=T.MathUtils.radToDeg(named.GUN_PITCH_PIVOT.rotation.z).toFixed(1)+'°';$('#traverse').textContent=aimYaw.toFixed(1)+'°';$('#yaw-control').value=aimYaw;$('#elevation-control').value=aimElevation;$('#hatch').textContent=Math.round(Math.abs(named.HATCH_L_PIVOT.rotation.z)*180/Math.PI/80*100)+'%';$('#recoil').textContent=Math.round(Math.abs(named.GUN_RECOIL_ROOT.position.x)*1000)+' mm';$('#fx-state').textContent=motion!=='shoot'?'待发':clock<.22?'炮口闪焰':clock<1.3?'烟尘扩散':clock<2.6?'烟尘消散':'结束';}
 function render(now){const dt=Math.min((now-last)/1000,.1);last=now;if(!paused)clock+=dt;applyMotion();if(motion==='shoot'&&clock>=2.8&&!paused){clock=2.8;paused=true;$('#pause').textContent='重播';$('#motion').textContent='开火完成';}if(wantExplode||exploded>.001){exploded=T.MathUtils.damp(exploded,wantExplode,5,dt);for(const n of separated)n.position.copy(rest.get(n)).addScaledVector(cachedSep.get(n),exploded);}world.updateMatrixWorld(true);updateInstances();frameTurret(dt);if(motion==='shoot')shotFX.update(clock,named.SOCKET_MUZZLE);renderer.render(world,camera);updateReadouts();
   $('.legend').style.visibility=Math.abs(aimYaw)<.1&&!wantExplode?'visible':'hidden';
   for(const m of markers){const p=m.p.clone().project(camera);m.el.style.display=view==='iso'&&!motion&&!wantExplode&&Math.abs(aimYaw)<.1?'grid':'none';m.el.style.left=(p.x*.5+.5)*innerWidth+'px';m.el.style.top=(-p.y*.5+.5)*innerHeight+'px';}
  requestAnimationFrame(render);}
 status.textContent='可旋转 · 可播放';document.body.dataset.ready='true';requestAnimationFrame(render);
 // Diagnostic state and deterministic seeking for local interaction checks.
 window.ferdinandInspection={snapshot:()=>({view,motion,paused,clock,exploded,nodeCount:nodes.length,trackCount:trackNodes.length,trackPosition:trackNodes[0].position.toArray(),recoil:named.GUN_RECOIL_ROOT.position.x,elevation:named.GUN_PITCH_PIVOT.rotation.z,hatch:named.HATCH_L_PIVOT.rotation.z,drawCalls:renderer.info.render.calls,flashVisible:shotFX.flash.visible&&shotFX.group.visible,smokeCount:shotFX.group.visible?shotFX.activePuffs:0}),seek:time=>{motion='';shotFX.clear();mixer.setTime(time);world.updateMatrixWorld(true);updateInstances();renderer.render(world,camera);updateReadouts();}};
})();
