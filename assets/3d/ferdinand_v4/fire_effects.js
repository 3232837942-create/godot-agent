/* Procedural presentation effects, in world space; no external textures. */
'use strict';
class FerdinandFireEffects {
 constructor(world) {
  const T=THREE;this.group=new T.Group();this.group.name='PRESENTATION_FIRE_FX';world.add(this.group);
  this.origin=new T.Vector3();this.orientation=new T.Quaternion();this.group.visible=false;
  this.flash=new T.Group();this.group.add(this.flash);this.flames=[];
  const flameShape=new T.LatheGeometry([new T.Vector2(.025,0),new T.Vector2(.17,.12),new T.Vector2(.29,.33),new T.Vector2(.13,.65),new T.Vector2(0,1.15)],9);flameShape.rotateZ(-Math.PI/2);
  for(const [angle,scale] of [[0,1],[1.25,.58],[-1.25,.58]]) {
   const material=new T.MeshBasicMaterial({color:0xf2ba72,transparent:true,opacity:.72,depthWrite:false});
   const plume=new T.Mesh(flameShape,material);plume.rotation.y=angle;plume.scale.setScalar(scale);this.flash.add(plume);this.flames.push(plume);
   const core=new T.Mesh(flameShape,new T.MeshBasicMaterial({color:0xfff1c3,transparent:true,opacity:.94,depthWrite:false}));core.scale.set(.72,.48,.48);plume.add(core);
   const outline=new T.LineSegments(new T.EdgesGeometry(flameShape,32),new T.LineBasicMaterial({color:0x966141,transparent:true,opacity:.38,depthWrite:false}));plume.add(outline);
  }
  this.wave=new T.Mesh(new T.TorusGeometry(1,.013,5,64),new T.MeshBasicMaterial({color:0x849bab,transparent:true,opacity:0,depthWrite:false}));this.wave.rotation.y=Math.PI/2;this.waveRoot=new T.Group();this.waveRoot.add(this.wave);this.group.add(this.waveRoot);
  this.puffs=[];const puffGeometry=new T.IcosahedronGeometry(1,2);
  const vertex='varying vec3 vN; varying vec3 vEye; void main(){vec4 p=modelViewMatrix*vec4(position,1.);vN=normalize(normalMatrix*normal);vEye=normalize(-p.xyz);gl_Position=projectionMatrix*p;}';
  const fragment='varying vec3 vN;varying vec3 vEye;uniform float alpha;uniform vec3 tint;void main(){float rim=pow(abs(dot(normalize(vN),normalize(vEye))),.7);float hatch=smoothstep(.82,1.,sin((gl_FragCoord.x+gl_FragCoord.y*.65)*.57));gl_FragColor=vec4(tint*(1.-hatch*.10),alpha*rim);}';
  for(let i=0;i<22;i++) {
   const dust=i>=16;const mat=new T.ShaderMaterial({vertexShader:vertex,fragmentShader:fragment,uniforms:{alpha:{value:0},tint:{value:dust?new T.Vector3(.72,.70,.66):new T.Vector3(.55,.62,.70)}},transparent:true,depthWrite:false});
   const mesh=new T.Mesh(puffGeometry,mat);mesh.visible=false;this.group.add(mesh);this.puffs.push({mesh,dust,index:i,seed:(Math.sin(i*78.233+4)*43758.5453)%1});
  }
  this.time=-1;this.activePuffs=0;
 }
 capture(socket) {socket.getWorldPosition(this.origin);socket.getWorldQuaternion(this.orientation);}
 clear() {this.group.visible=false;this.time=-1;this.activePuffs=0;}
 update(t,socket) {
  const T=THREE;this.time=t;this.group.visible=t>=0&&t<2.8;if(!this.group.visible)return;
  socket.getWorldPosition(this.flash.position);socket.getWorldQuaternion(this.flash.quaternion);
  const flashEnvelope=t<.22?Math.sin(Math.PI*Math.min(1,t/.22))**.65:0;
  this.flash.visible=flashEnvelope>.005;this.flash.scale.setScalar(flashEnvelope);
  this.waveRoot.position.copy(this.origin);this.waveRoot.quaternion.copy(this.orientation);this.wave.position.x=.1+t*1.5;this.wave.scale.setScalar(.1+t*2.4);this.wave.material.opacity=t<.5?.38*(1-t/.5):0;this.wave.visible=t<.5;
  this.activePuffs=0;
  for(const p of this.puffs) {
   const seed=Math.abs(p.seed),side=p.index%2?1:-1,age=t-(p.dust?.08:.10+.023*(p.index%6));const life=p.dust?1.55:2.35;
   p.mesh.visible=age>=0&&age<life;if(!p.mesh.visible)continue;this.activePuffs++;
   const f=age/life;const local=new T.Vector3();
   if(p.dust){local.set(.1+seed*.9,0,side*(.25+age*.8+seed*.3));local.applyQuaternion(this.orientation).add(this.origin);local.y=.055+age*.05;p.mesh.scale.set(.36+f*.6,.055+f*.11,.20+f*.6);}
   else {const sideJet=p.index<6;local.set(.12+seed*.45+age*(sideJet?.36:.8+seed*.9),age*(.22+seed*.26),side*(sideJet?.15+age*.68:.1+seed*.22+age*.15));local.applyQuaternion(this.orientation).add(this.origin);local.y+=age*.10;const r=.055+(sideJet?.18:.21)*Math.sqrt(age)+seed*.10;p.mesh.scale.set(r*(1+seed*.5),r*.9,r);}
   p.mesh.position.copy(local);p.mesh.rotation.set(seed*3+age*.15,seed*5,age*.2);p.mesh.material.uniforms.alpha.value=.14*Math.min(1,age/.09)*(1-f)**1.4;
  }
 }
}
