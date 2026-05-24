package de.haw.drift;

import org.eclipse.jdt.core.dom.*;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.ArrayList;
import java.util.List;

/**
 * Java AST Scanner — Main entry point.
 *
 * Usage:  java -jar java-scanner.jar <path>
 *
 * Scans all .java files under <path> and outputs JSON to stdout:
 * {
 *   "static":  [ { variable, file, line, method, has_default } ... ],
 *   "dynamic": [ { file, line, method } ... ]
 * }
 */
public class JavaScanner {

    private static final String[] SOURCE_DIRS  = new String[0];
    private static final String[] ENCODINGS    = new String[0];
    private static final String   JAVA_VERSION = "17";

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("Usage: java -jar java-scanner.jar <source-path>");
            System.exit(1);
        }

        Path root = Paths.get(args[0]);
        if (!Files.exists(root)) {
            System.err.println("Path not found: " + root);
            System.exit(1);
        }

        List<EnvReference> allRefs = scanPath(root);

        JSONObject output = new JSONObject();
        JSONArray staticArr  = new JSONArray();
        JSONArray dynamicArr = new JSONArray();

        for (EnvReference ref : allRefs) {
            if (ref.isDynamic) {
                JSONObject obj = new JSONObject();
                obj.put("file",   ref.file);
                obj.put("line",   ref.line);
                obj.put("method", ref.method);
                dynamicArr.put(obj);
            } else {
                JSONObject obj = new JSONObject();
                obj.put("variable",    ref.variable);
                obj.put("file",        ref.file);
                obj.put("line",        ref.line);
                obj.put("method",      ref.method);
                obj.put("has_default", ref.hasDefault);
                staticArr.put(obj);
            }
        }

        output.put("static",  staticArr);
        output.put("dynamic", dynamicArr);
        System.out.println(output.toString(2));
    }

    // ── Scan a file or directory recursively ──────────────────────────────────
    public static List<EnvReference> scanPath(Path root) throws IOException {
        List<EnvReference> results = new ArrayList<>();

        if (Files.isRegularFile(root) && root.toString().endsWith(".java")) {
            results.addAll(scanFile(root));
        } else if (Files.isDirectory(root)) {
            Files.walk(root)
                 .filter(p -> p.toString().endsWith(".java"))
                 .filter(p -> !isTestPath(p))
                 .forEach(p -> {
                     try { results.addAll(scanFile(p)); }
                     catch (IOException e) { /* skip unreadable files */ }
                 });
        }
        return results;
    }

    // ── Parse a single .java file ─────────────────────────────────────────────
    public static List<EnvReference> scanFile(Path file) throws IOException {
        String source = Files.readString(file, StandardCharsets.UTF_8);

        ASTParser parser = ASTParser.newParser(AST.JLS_Latest);
        parser.setSource(source.toCharArray());
        parser.setKind(ASTParser.K_COMPILATION_UNIT);
        parser.setResolveBindings(false);

        // Set compiler options
        java.util.Map<String, String> opts = org.eclipse.jdt.core.JavaCore.getDefaultOptions();
        opts.put(org.eclipse.jdt.core.JavaCore.COMPILER_SOURCE,
                 org.eclipse.jdt.core.JavaCore.VERSION_11);
        opts.put(org.eclipse.jdt.core.JavaCore.COMPILER_COMPLIANCE,
                 org.eclipse.jdt.core.JavaCore.VERSION_11);
        opts.put(org.eclipse.jdt.core.JavaCore.COMPILER_CODEGEN_TARGET_PLATFORM,
                 org.eclipse.jdt.core.JavaCore.VERSION_11);
        parser.setCompilerOptions(opts);

        CompilationUnit cu = (CompilationUnit) parser.createAST(null);
        JavaEnvVisitor visitor = new JavaEnvVisitor(file.toAbsolutePath().toString(), cu);
        cu.accept(visitor);
        return visitor.found;
    }

    private static boolean isTestPath(Path p) {
        String s = p.toString().replace('\\', '/');
        return s.contains("/test/") || s.contains("/tests/") || s.endsWith("Test.java");
    }
}
