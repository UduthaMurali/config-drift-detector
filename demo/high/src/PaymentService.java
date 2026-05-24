package com.example;
import org.springframework.beans.factory.annotation.Value;

public class PaymentService {
    @Value("${stripe.secret.key}")
    private String stripeKey;        // maps to STRIPE_SECRET_KEY - already counted
}
