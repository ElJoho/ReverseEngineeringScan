// Post-script: vuelca las entradas de la vtable de una clase C++ (Itanium ABI).
// Argumento: nombre completo de la clase, ej. libobsensor::VendorCommand.
// Ojo: el puntero del objeto apunta a la primera entrada después de offset-to-top y typeinfo,
// así que "vptr+0x60" corresponde a la entrada 0x60 bytes después del primer destructor.
//@category REA
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Symbol;

public class VtableSlots extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String cls = getScriptArgs()[0];
        for (Symbol s : currentProgram.getSymbolTable().getAllSymbols(true)) {
            if (!s.getName(true).equals(cls + "::vtable")) continue;
            Address base = s.getAddress().add(16);
            println("VT " + cls + " @" + s.getAddress());
            for (int i = 0; i < 40; i++) {
                Address p = toAddr(getLong(base.add(i * 8)));
                Function f = getFunctionAt(p);
                println(String.format("VT +0x%02x %s", i * 8, f == null ? p.toString() : f.getName(true)));
            }
        }
    }
}
