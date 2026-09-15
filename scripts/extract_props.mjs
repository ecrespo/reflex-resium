import ts from "typescript";
import fs from "fs";
const entry = "node_modules/resium/dist/index.d.ts";
const program = ts.createProgram([entry], { strict: true, jsx: 4, moduleResolution: 100, module: 99, target: 9, skipLibCheck: true });
const checker = program.getTypeChecker();
const sf = program.getSourceFile(entry);
const modSym = checker.getSymbolAtLocation(sf);
const out = {};
const fmt = (t) => checker.typeToString(t, undefined, ts.TypeFormatFlags.NoTruncation | ts.TypeFormatFlags.UseAliasDefinedOutsideCurrentScope);
function flags(t) {
  const parts = t.isUnion() ? t.types : [t];
  const kinds = new Set();
  for (const p of parts) {
    if (p.flags & ts.TypeFlags.Undefined) continue;
    if (p.flags & (ts.TypeFlags.BooleanLike)) kinds.add("boolean");
    else if (p.flags & ts.TypeFlags.NumberLike) kinds.add("number");
    else if (p.flags & ts.TypeFlags.StringLike) kinds.add("string");
    else if (p.flags & ts.TypeFlags.Null) kinds.add("null");
    else if (checker.getSignaturesOfType(p, ts.SignatureKind.Call).length) kinds.add("function");
    else if (checker.isArrayType(p)) kinds.add("array");
    else kinds.add("object:" + fmt(p));
  }
  return [...kinds];
}
for (const exp of checker.getExportsOfModule(modSym)) {
  const name = exp.getName();
  if (!/^[A-Z]/.test(name)) continue;
  const sym = exp.flags & ts.SymbolFlags.Alias ? checker.getAliasedSymbol(exp) : exp;
  if (!(sym.flags & ts.SymbolFlags.Value)) continue;
  const t = checker.getTypeOfSymbolAtLocation(sym, sf);
  const sigs = checker.getSignaturesOfType(t, ts.SignatureKind.Call);
  if (!sigs.length || !sigs[0].parameters.length) continue;
  const pt = checker.getTypeOfSymbolAtLocation(sigs[0].parameters[0], sf);
  const props = [];
  for (const p of checker.getPropertiesOfType(pt)) {
    const pn = p.getName();
    if (pn === "ref" || pn === "key") continue;
    const ptype = checker.getTypeOfSymbolAtLocation(p, sf);
    const doc = ts.displayPartsToString(p.getDocumentationComment(checker));
    const entry = { name: pn, type: fmt(ptype), kinds: flags(ptype), doc, optional: !!(p.flags & ts.SymbolFlags.Optional) };
    const nonUndef = ptype.isUnion() ? ptype.types.filter(x => !(x.flags & ts.TypeFlags.Undefined)) : [ptype];
    const fn = nonUndef.find(x => checker.getSignaturesOfType(x, ts.SignatureKind.Call).length);
    if (fn) {
      const s = checker.getSignaturesOfType(fn, ts.SignatureKind.Call)[0];
      entry.params = s.parameters.map(pp => ({ name: pp.getName(), type: fmt(checker.getTypeOfSymbolAtLocation(pp, sf)) }));
    }
    props.push(entry);
  }
  out[name] = props;
}
fs.writeFileSync("props.json", JSON.stringify(out, null, 1));
console.log(Object.keys(out).length, Object.keys(out).join(" "));
