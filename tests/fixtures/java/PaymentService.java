package com.example;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Sample Java Spring Boot service — test fixture for Java scanner.
 */
@Service
public class PaymentService {

    // Method 1: @Value annotation — maps to env var STRIPE_SECRET
    @Value("${stripe.secret}")
    private String stripeSecret;

    // Method 2: @Value with default — has_default = true
    @Value("${payment.timeout:5000}")
    private int timeoutMs;

    // Method 3: System.getenv() — direct call
    private final String apiKey = System.getenv("API_KEY");

    // Method 4: System.getenv() — INTENTIONALLY MISSING from config
    private final String webhookUrl = System.getenv("STRIPE_WEBHOOK_URL");

    public void processPayment(double amount) {
        // Method 5: inline System.getenv
        String dbUrl = System.getenv("DATABASE_URL");
        System.out.println("Processing payment: " + amount);
    }
}
