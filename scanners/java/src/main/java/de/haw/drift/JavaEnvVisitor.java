package de.haw.drift;

import org.eclipse.jdt.core.dom.*;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * ASTVisitor that detects all environment variable references in a Java source file.
 *
 * Detects:
 *   1. System.getenv("KEY")
 *   2. System.getenv().get("KEY")
 *   3. @Value("${KEY}")  /  @Value("${KEY:default}")
 *   4. environment.getProperty("KEY")  /  environment.getProperty("KEY","default")
 *   5. @ConfigurationProperties(prefix="...")
 *   6. ${KEY} placeholders in @Value strings
 */
public class JavaEnvVisitor extends ASTVisitor {

    private final String filename;
    private final CompilationUnit cu;
    public final List<EnvReference> found = new ArrayList<>();

    // Matches ${KEY}  or  ${KEY:defaultValue}
    private static final Pattern VALUE_PLACEHOLDER =
        Pattern.compile("\\$\\{([A-Za-z0-9_.\\-]+)(?::([^}]*))?\\}");

    // Converts Spring property key (app.db.url) → env var (APP_DB_URL)
    private static String toEnvVar(String springKey) {
        return springKey.toUpperCase().replace('.', '_').replace('-', '_');
    }

    public JavaEnvVisitor(String filename, CompilationUnit cu) {
        this.filename = filename;
        this.cu = cu;
    }

    // ── 1 & 2 : System.getenv("KEY")  /  System.getenv().get("KEY") ──────────
    @Override
    public boolean visit(MethodInvocation node) {
        String name = node.getName().getIdentifier();

        // System.getenv("KEY")
        if ("getenv".equals(name)) {
            Expression expr = node.getExpression();
            if (expr instanceof SimpleName && "System".equals(((SimpleName) expr).getIdentifier())) {
                if (!node.arguments().isEmpty()) {
                    Object arg = node.arguments().get(0);
                    if (arg instanceof StringLiteral) {
                        String key = ((StringLiteral) arg).getLiteralValue();
                        addRef(key, node, "System.getenv()", false, false);
                    } else {
                        addRef("<dynamic>", node, "System.getenv(expr)", false, true);
                    }
                }
            }
        }

        // environment.getProperty("KEY")  /  environment.getProperty("KEY","default")
        if ("getProperty".equals(name)) {
            if (!node.arguments().isEmpty()) {
                Object arg = node.arguments().get(0);
                if (arg instanceof StringLiteral) {
                    String key = ((StringLiteral) arg).getLiteralValue();
                    boolean hasDef = node.arguments().size() > 1;
                    String envKey = toEnvVar(key);
                    addRef(envKey, node, "environment.getProperty()", hasDef, false);
                }
            }
        }

        return true;
    }

    // ── 3 : @Value("${KEY}") ─────────────────────────────────────────────────
    @Override
    public boolean visit(SingleMemberAnnotation node) {
        if ("Value".equals(node.getTypeName().getFullyQualifiedName())) {
            Object val = node.getValue();
            if (val instanceof StringLiteral) {
                String text = ((StringLiteral) val).getLiteralValue();
                Matcher m = VALUE_PLACEHOLDER.matcher(text);
                while (m.find()) {
                    String springKey = m.group(1);
                    boolean hasDef = m.group(2) != null;
                    String envKey = toEnvVar(springKey);
                    addRef(envKey, node, "@Value(${" + springKey + "})", hasDef, false);
                }
            }
        }
        return true;
    }

    // ── 5 : @ConfigurationProperties(prefix="my.app") ────────────────────────
    @Override
    public boolean visit(NormalAnnotation node) {
        if ("ConfigurationProperties".equals(node.getTypeName().getFullyQualifiedName())) {
            for (Object pairObj : node.values()) {
                if (pairObj instanceof MemberValuePair) {
                    MemberValuePair pair = (MemberValuePair) pairObj;
                    if ("prefix".equals(pair.getName().getIdentifier())) {
                        Expression val = pair.getValue();
                        if (val instanceof StringLiteral) {
                            String prefix = ((StringLiteral) val).getLiteralValue();
                            addRef(toEnvVar(prefix) + "_*", node,
                                   "@ConfigurationProperties(prefix)", false, false);
                        }
                    }
                }
            }
        }
        return true;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    private void addRef(String variable, ASTNode node, String method,
                        boolean hasDefault, boolean isDynamic) {
        int line = cu.getLineNumber(node.getStartPosition());
        found.add(new EnvReference(variable, filename, line, method, hasDefault, isDynamic));
    }
}
