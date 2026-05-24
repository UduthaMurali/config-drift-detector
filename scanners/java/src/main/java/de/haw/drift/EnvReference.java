package de.haw.drift;

/**
 * Represents a single environment variable reference found in source code.
 */
public class EnvReference {
    public final String variable;
    public final String file;
    public final int line;
    public final String method;
    public final boolean hasDefault;
    public final boolean isDynamic;

    public EnvReference(String variable, String file, int line,
                        String method, boolean hasDefault, boolean isDynamic) {
        this.variable   = variable;
        this.file       = file;
        this.line       = line;
        this.method     = method;
        this.hasDefault = hasDefault;
        this.isDynamic  = isDynamic;
    }
}
