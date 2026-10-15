import {AbsoluteFill, useCurrentFrame} from 'remotion';
import speech from './speech.json';

// The camera never moves. Every pose is a pure function of the video frame.
export const FPS = 30;
export const FRAMES = 300;
type Point = [number, number];
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
const clamp = (v: number) => Math.max(0, Math.min(1, v));
const ease = (t: number) => {const k = clamp(t); return k * k * (3 - 2 * k);};
const between = (t: number, a: number, b: number) => ease((t - a) / (b - a));
const blend = (a: Point, b: Point, u: number): Point => [mix(a[0], b[0], u), mix(a[1], b[1], u)];
const skin = '#f8b5dd';
const pink = '#e88cbd';
const mouthColor = '#c25a90';

function Blink({x, y, look, openness}: {x: number; y: number; look: Point; openness: number}) {
  return <g transform={`translate(${x} ${y})`}>
    {openness < 0.2 ? <path d="M-11 1 Q0 7 11 1" fill="none" stroke={pink} strokeWidth="3.5"/> :
      <g transform={`scale(1 ${Math.max(0.15, openness)})`}>
        <ellipse rx="13" ry="15" fill="white" stroke={pink} strokeWidth="3"/>
        <circle cx={look[0]} cy={look[1]} r="5.1" fill="#17141a"/>
      </g>}
  </g>;
}

function eyelids(frame: number, events: number[]) {
  const d = Math.min(...events.map(e => Math.abs(frame - e)));
  return d >= 4 ? 1 : 1 - Math.cos(d / 4 * Math.PI / 2) ** 2;
}

function Mouth({amount, frame}: {amount: number; frame: number}) {
  if (amount < 0.12) return <path d="M6 -37 Q25 -7 54 -35" fill="none" stroke={mouthColor} strokeWidth="5.5" strokeLinecap="round"/>;
  if (Math.floor(frame / 4) % 4 === 2) return <ellipse cx="30" cy="-26" rx={9 + amount * 5} ry={5 + amount * 10} fill="#392337" stroke={mouthColor} strokeWidth="4"/>;
  return <path d={`M6 -38 Q28 -21 56 -37 Q54 ${-13 + amount * 13} 30 ${-10 + amount * 14} Q10 ${-12 + amount * 11} 6 -38Z`} fill="#392337" stroke={mouthColor} strokeWidth="4" strokeLinejoin="round"/>;
}

function Head({frame, george, angle, look, amount}: {frame: number; george?: boolean; angle: number; look: Point; amount: number}) {
  return <g transform={`rotate(${angle} 0 -35)`} data-part={george ? 'george-head' : 'peppa-head'}>
    <g transform={george ? 'scale(-1 1)' : undefined}>
      <ellipse cx="-59" cy="-146" rx="15" ry="31" fill={skin} stroke={pink} strokeWidth="5" transform="rotate(-18 -59 -146)"/>
      <ellipse cx="-8" cy="-154" rx="14" ry="30" fill={skin} stroke={pink} strokeWidth="5" transform="rotate(11 -8 -154)"/>
      <path d="M-65 -126 C-31 -146 32 -142 78 -119 C103 -126 137 -119 146 -98 C157 -74 138 -55 109 -56 L75 -54 C81 -22 59 9 27 24 C-13 43 -74 31 -97 -4 C-121 -42 -109 -100 -65 -126Z" fill={skin} stroke={pink} strokeWidth="5" strokeLinejoin="round"/>
      <ellipse cx="122" cy="-91" rx="26" ry="29" fill="#fac3e5" stroke={pink} strokeWidth="5" transform="rotate(-18 122 -91)"/>
      <ellipse cx="114" cy="-94" rx="4" ry="5" fill="#ce70aa"/>
      <ellipse cx="129" cy="-88" rx="4" ry="5" fill="#ce70aa"/>
      <circle cx="-56" cy="-39" r="22" fill="#f39bd5"/>
      <Blink x={18} y={-109} look={look} openness={eyelids(frame, george ? [54, 187, 272] : [81, 169, 261])}/>
      <Blink x={62} y={-106} look={look} openness={eyelids(frame, george ? [54, 187, 272] : [81, 169, 261])}/>
      <Mouth amount={amount} frame={frame}/>
      {george && <g data-part="hearing-aid">
        <path d="M-23 -145 C-32 -171 -8 -183 2 -167 L4 -151" stroke="#9b9eac" strokeWidth="7" fill="none" strokeLinecap="round"/>
        <path d="M-19 -148 C-25 -164 -10 -170 -5 -159" stroke="#70c9d3" strokeWidth="7" fill="none" strokeLinecap="round"/>
        <ellipse cx="-3" cy="-151" rx="5" ry="7" fill="#80d4db"/>
      </g>}
    </g>
  </g>;
}

function Torso({x, y, scale, george}: {x: number; y: number; scale: number; george?: boolean}) {
  return <g transform={`translate(${x} ${y}) scale(${scale})`}>
    <path d={george ? 'M62 112 C101 133 104 93 85 99 C65 104 84 136 109 118' : 'M-72 117 C-115 139 -126 104 -108 103 C-91 101 -96 137 -127 122'} stroke={skin} strokeWidth="7" fill="none" strokeLinecap="round"/>
    <path d="M-36 146 L-38 182 M37 146 L40 182" stroke={skin} strokeWidth="7" strokeLinecap="round"/>
    <path d="M-37 183 L-60 183 M40 183 L62 183" stroke="#17141a" strokeWidth="12" strokeLinecap="round"/>
    <path d={george ? 'M-42 16 C-77 20 -87 82 -76 121 C-64 164 63 161 78 122 C89 84 76 24 42 16Z' : 'M-39 18 C-66 35 -79 103 -87 153 L84 153 C78 100 64 40 37 18Z'} fill={george ? '#6b9ed4' : '#eb646a'} stroke={george ? '#5289c3' : '#df535e'} strokeWidth="5" strokeLinejoin="round"/>
  </g>;
}

function Hand({at, angle = 0}: {at: Point; angle?: number}) {
  return <g transform={`translate(${at[0]} ${at[1]}) rotate(${angle})`} fill="none" stroke={skin} strokeWidth="6.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M-5 0 L8 -10 M-4 1 L12 1 M-3 2 L6 12"/>
  </g>;
}

function Arm({from, elbow, to}: {from: Point; elbow: Point; to: Point}) {
  return <path d={`M${from.join(' ')} Q${elbow.join(' ')} ${to.join(' ')}`} stroke={skin} strokeWidth="7" strokeLinecap="round" fill="none"/>;
}

export function Crayon({tip, angle, color, outline, id}: {tip: Point; angle: number; color: string; outline: string; id: string}) {
  return <g transform={`translate(${tip[0]} ${tip[1]}) rotate(${angle})`} data-object={id} stroke={outline} strokeWidth="2.5" strokeLinejoin="round">
    <path d="M0 0 L-6 -12 V-49 Q0 -54 6 -49 V-12Z" fill={color}/>
    <path d="M-6 -12 H6 M-6 -42 H6 M-6 -37 H6" fill="none"/>
    <path d="M0 -1 L-4 -10 H4Z" fill={outline} stroke="none"/>
  </g>;
}
const grip = (tip: Point, angle: number): Point => [tip[0] + Math.sin(angle * Math.PI / 180) * 31, tip[1] - Math.cos(angle * Math.PI / 180) * 31];

type Stroke = {start: number; end: number; points: Point[]; color: string};
const strokes: Stroke[] = [
  {start: 1.18, end: 2.58, color: '#468ec6', points: [[548,612],[548,599],[546,589],[552,588],[557,597],[572,597],[579,587],[585,588],[583,600],[589,606],[586,618],[576,624],[557,624],[548,619],[548,612]]},
  {start: 2.85, end: 3.8, color: '#468ec6', points: [[558,626],[553,643],[579,644],[576,626],[575,631],[588,633]]},
  {start: 4.05, end: 4.55, color: '#468ec6', points: [[554,633],[542,630],[538,635]]},
  {start: 8.2, end: 9.05, color: '#468ec6', points: [[622,641],[627,636],[636,635],[644,639],[647,646],[643,652],[633,655],[625,651],[622,641]]},
  {start: 8.35, end: 9.5, color: '#39a86a', points: [[806,643],[800,637],[798,627],[803,620],[813,616],[826,617],[820,623],[827,626],[817,630],[817,642],[811,647],[797,647],[788,642],[780,638],[789,642],[802,645]]},
];
function strokePoint(s: Stroke, time: number): {point: Point; points: Point[]} {
  const progress = clamp((time - s.start) / (s.end - s.start));
  const lengths = s.points.slice(1).map((p, i) => Math.hypot(p[0] - s.points[i][0], p[1] - s.points[i][1]));
  const distance = progress * lengths.reduce((a,b) => a+b,0);
  let soFar = 0;
  for (let i = 0; i < lengths.length; i++) {
    if (distance <= soFar + lengths[i] || i === lengths.length - 1) {
      const point = blend(s.points[i], s.points[i+1], clamp((distance-soFar)/lengths[i]));
      return {point, points: [...s.points.slice(0,i+1), point]};
    }
    soFar += lengths[i];
  }
  return {point:s.points[0], points:[s.points[0]]};
}

function peppaPen(t: number): Point {
  const active = strokes.filter(s => s.color === '#468ec6');
  if (t < active[0].start) return blend([533,550], active[0].points[0], between(t,0.8,active[0].start));
  for(let i=0;i<active.length;i++) {
    const s=active[i];
    if(t <= s.end) return strokePoint(s,t).point;
    const next=active[i+1];
    if(next && t < next.start) {
      if(next.start-s.end>2) {
        const park:Point=[552,575];
        if(t<s.end+.4)return blend(s.points[s.points.length-1],park,between(t,s.end,s.end+.4));
        return blend(park,next.points[0],between(t,next.start-.4,next.start));
      }
      const u=clamp((t-s.end)/(next.start-s.end));
      const p=blend(s.points.at(-1)!,next.points[0],ease(u));
      p[1]-=Math.sin(Math.PI*u)*25;
      return p;
    }
  }
  const last=active.at(-1)!;
  return blend(last.points.at(-1)!,[612,562],between(t,last.end,9.65));
}

export function getPose(frame: number) {
  const t = frame/FPS;
  const blueTip=peppaPen(t);
  let greenTip:Point=[861,557]; let greenAngle=85;
  const pick=5.6;
  if(t>=pick && t<6.45) {const u=between(t,pick,6.45);greenTip=blend([861,557],[852,513],u);greenAngle=mix(85,-18,u);}
  else if(t>=6.45 && t<8.35) {greenTip=blend([852,513],strokes[4].points[0],between(t,7.85,8.35));greenAngle=-18;}
  else if(t>=8.35) {greenTip=strokePoint(strokes[4],t).point;greenAngle=-18; if(t>9.5)greenTip=blend(greenTip,[818,593],between(t,9.5,9.95));}
  const greenGrip=grip(greenTip,greenAngle);
  const georgeHand=t<pick?blend([823,567],grip([861,557],85),between(t,4.7,pick)):greenGrip;
  return {t,blueTip,blueGrip:grip(blueTip,-28),greenTip,greenGrip,greenAngle,georgeHand,greenHeld:t>=pick};
}

function Kitchen() {
  return <g data-layer="fixed-kitchen">
    <rect width="1280" height="720" fill="#fff2ad"/>
    <path d="M0 435 H1280 V720 H0Z" fill="#b8d2f0"/>
    <rect x="20" y="37" width="111" height="91" rx="2" fill="#fff9d7" stroke="#e2bb70" strokeWidth="6"/>
    <path d="M29 104 Q52 80 86 102 T123 94 V119 H29Z" fill="#87c977"/>
    <circle cx="63" cy="66" r="14" fill="#ffe570"/>
    <circle cx="227" cy="93" r="52" fill="#fffefd" stroke="#85b9eb" strokeWidth="7"/>
    {[0,1,2,3,4,5,6,7,8,9,10,11].map(i=><path key={i} d="M0 -42 V-35" stroke="#a2b2c3" strokeWidth="3" transform={`translate(227 93) rotate(${i*30})`}/>)}
    <path d="M227 63 V93 L202 77" stroke="#74818c" strokeWidth="5" strokeLinecap="round" fill="none"/>
    <rect x="466" y="23" width="334" height="223" fill="#8dc4ee" stroke="#fdfdf4" strokeWidth="9"/>
    <path d="M470 212 Q542 160 625 211 Q711 177 796 205 V242 H470Z" fill="#8bc97d"/>
    <circle cx="542" cy="83" r="24" fill="#ffe470"/>
    <path d="M678 72 C672 51 704 43 713 60 C729 45 754 61 749 77 C774 91 749 107 731 99 H690 C667 99 658 82 678 72Z" fill="#fffef3"/>
    <path d="M633 26 V244 M468 137 H798" stroke="#fdfdf4" strokeWidth="8"/>
    <path d="M431 10 H475 V253 Q449 238 426 251Z M791 10 H836 V251 Q811 237 789 250Z" fill="#90d397" stroke="#74c482" strokeWidth="5"/>
    {[38,96,155,216].map(y=><g key={y} fill="#a9dfa9"><circle cx="450" cy={y} r="7"/><circle cx="814" cy={y+15} r="7"/></g>)}
    <rect x="0" y="289" width="1095" height="167" fill="#91cac7" stroke="#78b6bc" strokeWidth="5"/>
    <path d="M201 291 V454 M427 291 V454 M658 291 V454 M886 291 V454" stroke="#78b6bc" strokeWidth="4"/>
    {[171,397,628,856,1057].map(x=><circle key={x} cx={x} cy="326" r="6" fill="#62a8ad"/>)}
    <path d="M0 260 H1094 V292 H0Z" fill="#d3dfed" stroke="#97b5ca" strokeWidth="5"/>
    <ellipse cx="633" cy="275" rx="92" ry="12" fill="#b8cbdc" stroke="#95b4c8" strokeWidth="4"/>
    <path d="M631 269 V231 Q631 198 657 198 Q681 198 681 224" fill="none" stroke="#a7bac9" strokeWidth="12" strokeLinecap="round"/>
    <path d="M575 265 V250 M710 266 V251" stroke="#a7bac9" strokeWidth="7"/>
    <circle cx="575" cy="249" r="7" fill="#e98383"/><circle cx="710" cy="250" r="7" fill="#85b4e6"/>
    <g transform="translate(-220 0)">
    <path d="M309 242 Q302 209 329 205 Q346 205 347 222 Q347 196 369 201 Q392 205 378 242" fill="#ef8484" stroke="#d56d72" strokeWidth="3"/>
    <path d="M293 233 H391 L379 268 H306Z" fill="#fdfdf4" stroke="#95bae4" strokeWidth="4"/>
    <path d="M304 248 H381" stroke="#95bae4" strokeWidth="4"/>
    </g>
    <rect x="1110" y="62" width="175" height="425" rx="30" fill="#fafaf2" stroke="#b3bac2" strokeWidth="5"/>
    <path d="M1110 233 H1280 M1130 164 V205 M1130 266 V309" stroke="#a7b4c1" strokeWidth="6" strokeLinecap="round"/>
    <path d="M1191 114 C1178 92 1157 106 1170 120 L1191 138 L1213 120 C1226 104 1203 91 1191 114Z" fill="#82b6e8"/>
    <path d="M1190 287 L1198 306 L1219 306 L1203 319 L1209 339 L1190 327 L1173 338 L1178 319 L1162 306 L1183 305Z" fill="#ffe27d" stroke="#edbf5c" strokeWidth="3"/>
  </g>;
}

function PaperArt({t}: {t: number}) {
  return <g strokeLinecap="round" strokeLinejoin="round">
    <path d="M378 568 H905 L956 675 H330Z" fill="#d1b976" opacity=".26" transform="translate(0 5)"/>
    <path d="M378 568 H905 L956 675 H330Z" fill="#fffef7"/>
    <g transform="translate(477 611) skewX(-12) scale(.58 .48)" fill="none" stroke="#e38bb5" strokeWidth="4">
      <path d="M-13 -17 Q-10 -38 15 -28 L33 -22 Q49 -17 35 -5 L20 -5 Q21 17 -2 16 Q-27 13 -22 -4Z M-13 -26 L-17 -43 L-7 -28 M4 -30 L9 -45 L15 -27 M-7 18 L-22 58 H22 L9 18 M-18 33 L-37 24 M16 33 L35 24 M-10 59 V73 M11 59 V73"/>
      <circle cx="10" cy="-18" r="2.5"/><circle cx="21" cy="-16" r="2.5"/>
    </g>
    <g transform="translate(710 612) skewX(-12) scale(.5 .45)" fill="none" stroke="#d980b2" strokeWidth="4">
      <path d="M-13 -17 Q-10 -38 15 -28 L33 -22 Q49 -17 35 -5 L20 -5 Q21 17 -2 16 Q-27 13 -22 -4Z M-13 -26 L-17 -43 L-7 -28 M4 -30 L9 -45 L15 -27"/>
      <path d="M-5 19 C-30 18 -32 58 1 60 C32 59 31 18 10 19 M-22 34 L-39 29 M22 34 L36 24 M-10 59 V73 M11 59 V73" stroke="#6aa2d1"/>
    </g>
    <g transform="translate(765 605) scale(.55 .58)" fill="none" stroke="#e3a46a" strokeWidth="3.4">
      <path d="M-14 9 L-15 -12 L-10 -14 L-4 -6 L5 -6 L9 -14 L14 -12 L13 9 Q13 24 -12 22Z M-8 23 L-14 57 H17 L9 23 M-11 37 L-27 32 M13 37 L28 29 M-6 58 V69 M10 58 V69"/>
      <circle cx="-4" cy="5" r="2" stroke="#434752"/><circle cx="6" cy="5" r="2" stroke="#434752"/><path d="M-1 15 H3" stroke="#434752"/>
    </g>
    {strokes.filter(s=>t>s.start).map((s,i)=><polyline key={i} points={strokePoint(s,t).points.map(p=>p.join(',')).join(' ')} fill="none" stroke={s.color} strokeWidth="2.7"/>)}
    {t>2.58 && <g fill="#344f6f"><circle cx="558" cy="608" r="1.8"/><circle cx="573" cy="607" r="1.8"/><ellipse cx="570" cy="616" rx="2.6" ry="1.7"/></g>}
    {t>9.05 && <path d="M628 643 L637 640 L642 647 L635 651 L628 647Z" fill="#526377"/>}
    {t>9.2 && <g fill="#2f8960"><circle cx="816" cy="620" r="1.6"/><path d="M804 647 L802 653 M810 647 L812 653" stroke="#39a86a" strokeWidth="2"/></g>}
  </g>;
}

export function SceneArtwork({frame}: {frame: number}) {
  const p=getPose(frame);
  const peppaAmount=speech.peppa[frame] || 0;
  const georgeAmount=speech.george[frame] || 0;
  const lookUp=between(p.t,4.85,5.45)*(1-between(p.t,7.75,8.15))+between(p.t,9.15,9.65);
  const peppaNod=Math.sin(p.t*5)*0.65*peppaAmount;
  const georgeNod=Math.sin(p.t*5.4)*0.9*georgeAmount;
  const gesture=Math.sin(Math.PI*clamp((p.t-4.55)/1.3))*45;
  const freeHand:Point=[1033-gesture*.25,558-gesture];
  return <svg width="1280" height="720" viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">
      <Kitchen/>
      <g data-layer="chairs" fill="#85b8e9" stroke="#6a9ed5" strokeWidth="6">
        <path d="M245 470 Q241 417 287 416 H435 Q474 417 475 460 L456 609 H267Z"/>
        <path d="M881 489 Q878 445 912 445 H1039 Q1084 446 1084 489 L1068 627 H897Z"/>
      </g>
      <Torso x={389} y={414} scale={1.1}/>
      <Torso x={947} y={448} scale={.84} george/>
      <g transform="translate(389 414) scale(1.1)">
        <Head frame={frame} angle={mix(-3,-9,lookUp)+peppaNod} look={[mix(3,4,lookUp),mix(5,2,lookUp)]} amount={peppaAmount}/>
      </g>
      <g transform="translate(947 448) scale(.84)">
        <Head frame={frame} george angle={8-5*between(p.t,4.7,5.6)+4*between(p.t,6.1,7.1)+georgeNod} look={[mix(3,1,between(p.t,5.6,6.4)),p.t>8.1?5:3]} amount={georgeAmount}/>
      </g>
      <ellipse cx="641" cy="655" rx="582" ry="146" fill="#dfbd68"/>
      <ellipse cx="641" cy="642" rx="582" ry="143" fill="#ffe18b" stroke="#ebc46b" strokeWidth="5"/>
      <PaperArt t={p.t}/>
      <g data-layer="crayon-cup">
        <Crayon id="red-in-cup" tip={[967,525]} angle={-12} color="#ed777b" outline="#c85765"/>
        <Crayon id="yellow-in-cup" tip={[990,526]} angle={9} color="#ffe079" outline="#d8b54a"/>
        <path d="M949 497 Q973 509 1004 497 L1002 545 Q975 560 950 545Z" fill="#87c99b" stroke="#66b380" strokeWidth="4"/>
        <path d="M950 497 Q975 488 1004 497" fill="none" stroke="#66b380" strokeWidth="4"/>
      </g>
      <Arm from={[335,478]} elbow={[346,558]} to={[410,577]}/><Hand at={[410,577]} angle={-20}/>
      <Arm from={[453,479]} elbow={[469,548]} to={p.blueGrip}/>
      <Crayon id="blue-single" tip={p.blueTip} angle={-28} color="#84b8e8" outline="#467cae"/>
      <Hand at={p.blueGrip} angle={-15}/>
      <Arm from={[993,496]} elbow={[1040,535-gesture*.7]} to={freeHand}/>
      <Hand at={freeHand} angle={170-gesture*.5}/>
      <Arm from={[893,493]} elbow={[878,533]} to={p.georgeHand}/>
      <Crayon id="green-single" tip={p.greenTip} angle={p.greenAngle} color="#6ac78f" outline="#388d64"/>
      <Hand at={p.georgeHand} angle={-8}/>
    </svg>;
}

export function DrawingScene() {
  const frame=useCurrentFrame();
  return <AbsoluteFill><SceneArtwork frame={frame}/></AbsoluteFill>;
}
