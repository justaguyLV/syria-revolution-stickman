// Renders stickman motion clips (SVG frames) using the open-source engine vallahrich/stickman-mcp.
// usage: node tools/make_clips.mjs <engine_dir> <out_dir>
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [engineDir, outDir] = process.argv.slice(2);
const eng = await import(pathToFileURL(path.join(engineDir, "dist", "index.js")).href);
const FPS = 24, CW = 220, CH = 260, GY = 236;          // crop window (px) and ground line

// name -> {dur, actions, travel}. travel clips are re-centred on the torso so they walk "in place".
const CLIPS = {
  idle:  { dur: 3000, actions: [{ action: "idle", startMs: 0, durationMs: 3000 }] },
  walk:  { dur: 3600, travel: true, actions: [{ action: "walk", startMs: 0, durationMs: 3600, target: "b" }] },
  run:   { dur: 3000, travel: true, actions: [{ action: "run", startMs: 0, durationMs: 3000, target: "b" }] },
  wave:  { dur: 2400, actions: [{ action: "wave", startMs: 0, durationMs: 2400 }] },
  point: { dur: 2400, actions: [{ action: "point", startMs: 0, durationMs: 2400, target: "p" }] },
  jump:  { dur: 2400, actions: [{ action: "jump", startMs: 0, durationMs: 1200 }, { action: "jump", startMs: 1200, durationMs: 1200 }] },
  stop:  { dur: 2000, actions: [{ action: "stop", startMs: 0, durationMs: 2000 }] },
};

fs.mkdirSync(outDir, { recursive: true });
const report = {};
for (const [name, c] of Object.entries(CLIPS)) {
  const wide = c.travel ? 1000 : 440;
  const spec = {
    version: "stickman.animation/v1",
    canvas: { width: wide, height: CH, fps: FPS },
    durationMs: c.dur,
    actor: { x: c.travel ? 120 : wide / 2, groundY: GY },
    targets: { b: { x: wide - 140, y: GY }, p: { x: wide / 2 + 160, y: GY - 110 } },
    actions: c.actions,
  };
  const r = eng.compileAnimation(spec);
  if (!r.valid) { console.error(name, JSON.stringify(r.diagnostics).slice(0, 600)); continue; }
  const dir = path.join(outDir, name); fs.mkdirSync(dir, { recursive: true });
  const n = Math.round(c.dur / 1000 * FPS);
  for (let i = 0; i < n; i++) {
    let svg = eng.renderSvgFrame(r.program, (i / FPS) * 1000);
    let cx = wide / 2;
    if (c.travel) {                                    // centre on torso x
      const m = svg.match(/id="torso" d="M([\d.-]+) [\d.-]+L([\d.-]+) /);
      if (m) cx = (parseFloat(m[1]) + parseFloat(m[2])) / 2;
    }
    svg = svg.replace(/<rect width="100%" height="100%"[^>]*\/>/, "")
             .replace(/<path id="ground"[^>]*\/>/, "")
             .replace(/viewBox="[^"]*" width="[^"]*" height="[^"]*"/, `viewBox="${(cx - CW / 2).toFixed(2)} 0 ${CW} ${CH}" width="${CW}" height="${CH}"`);
    fs.writeFileSync(path.join(dir, String(i).padStart(4, "0") + ".svg"), svg);
  }
  report[name] = n;
}
console.log(JSON.stringify(report));
