# Paddle Payment Testing Guide

## Overview
This document describes how to test the Paddle payment integration for the international version of AutoOverview.

## Environment Setup

### Development Environment (Sandbox)
The Paddle payment service runs in sandbox mode by default. Key configuration in `.env`:
```bash
IS_DEV=true
PADDLE_SANDBOX=true
PADDLE_API_KEY=your-paddle-api-key  # Get from Paddle dashboard
PADDLE_WEBHOOK_SECRET=your-paddle-webhook-secret
```

## Testing Scenarios

### 1. Backend API Testing

#### Test 1.1: Get Paddle Pricing Plans
```bash
curl http://localhost:8006/api/paddle/plans
```

Expected Response:
```json
{
  "plans": {
    "single": {
      "name": "Single Review",
      "price": 5.99,
      "credits": 1,
      "currency": "USD"
    },
    "semester": {
      "name": "Semester Pack",
      "price": 29.99,
      "credits": 10,
      "currency": "USD"
    },
    "yearly": {
      "name": "Academic Year Pack",
      "price": 79.99,
      "credits": 30,
      "currency": "USD"
    }
  }
}
```

#### Test 1.2: Create Paddle Checkout Session
```bash
curl -X POST http://localhost:8006/api/paddle/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_type": "single"}'
```

Expected Response:
```json
{
  "order_no": "PD20260411...",
  "checkout_url": "https://sandbox-checkout.paddle.com/...",
  "amount": 5.99,
  "currency": "USD"
}
```

### 2. Frontend Testing

#### Test 2.1: Language Switching
1. Open homepage: `http://localhost:3006`
2. Click language toggle to switch to English
3. Verify all UI text is in English
4. Check pricing displays in USD

#### Test 2.2: Paddle Payment Modal
1. Login to the application
2. Click on any pricing plan (e.g., "Buy Now")
3. Verify `PaddlePaymentModal` opens (not `PaymentModal`)
4. Check that prices are in USD
5. In development mode, payment should auto-complete in 3 seconds

#### Test 2.3: Payment Success Flow
1. Complete a payment (or wait for auto-payment in dev mode)
2. Verify success message appears
3. Check that credits are updated
4. Verify redirect to profile page

### 3. Development Mode Testing

#### Test 3.1: Mock Payment Flow
In development mode (`IS_DEV=true`), the payment flow is simulated:
1. Create order → generates mock checkout URL
2. Wait 3 seconds → auto-completes payment
3. Polling detects status change → activates subscription
4. Credits added to user account

#### Test 3.2: Webhook Testing (Development)
Development mode skips webhook signature verification:
```bash
curl -X POST http://localhost:8006/api/paddle/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "payment.success",
    "data": {
      "custom_data": {
        "order_no": "TEST_ORDER_ID"
      }
    }
  }'
```

## Production Deployment Checklist

### Before Going Live:
1. [ ] Update `.env` with production Paddle credentials
2. [ ] Set `PADDLE_SANDBOX=false`
3. [ ] Configure webhook URL in Paddle dashboard
4. [ ] Test real payment flow with test card
5. [ ] Verify webhook signature verification
6. [ ] Check email notifications are sent
7. [ ] Monitor logs for payment errors

### Paddle Dashboard Configuration:
1. Create products in Paddle dashboard
2. Set up prices (USD):
   - Single Review: $5.99
   - Semester Pack: $29.99
   - Academic Year Pack: $79.99
3. Configure webhook endpoint
4. Set up tax rules for different countries
5. Enable payment methods (credit cards, PayPal)

## Common Issues

### Issue 1: Payment Not Completing
**Solution**: Check that polling is running every 3 seconds in browser console

### Issue 2: Webhook Not Received
**Solution**: Verify webhook URL is accessible from internet (not localhost)

### Issue 3: Signature Verification Failed
**Solution**: Ensure `PADDLE_WEBHOOK_SECRET` matches Paddle dashboard

### Issue 4: Wrong Currency Displayed
**Solution**: Check language is set to 'en' for USD pricing

## Monitoring

### Key Metrics to Track:
1. Payment success rate
2. Average time to complete payment
3. Webhook response time
4. Credit allocation accuracy
5. User conversion rate

### Log Files:
- Backend: `/var/log/autooverview/paddle_payments.log`
- Webhook: `/var/log/autooverview/webhook.log`

## Support

For Paddle-related issues:
- Documentation: https://developer.paddle.com/
- Support: https://vendors.paddle.com/support
- Status Page: https://status.paddle.com/
