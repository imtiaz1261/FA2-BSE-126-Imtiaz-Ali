"""
prompts.py
----------
The same task, written 5 different ways using 5 different prompting
techniques. TASK_DESCRIPTION is what a person would naturally ask for;
each PROMPTS[...] entry is that same intent, engineered differently.
"""

TASK_DESCRIPTION = (
    "Write an email to a client informing them their order is delayed "
    "by one week, apologizing and offering a 10% discount on their "
    "next purchase."
)

PROMPTS = {

    "1_zero_shot": (
        "Write an email to a client informing them their order is delayed "
        "by one week. Apologize and offer a 10% discount on their next "
        "purchase."
    ),

    "2_few_shot": (
        "Here are two examples of professional client emails:\n\n"
        "Example 1:\n"
        "Subject: Update on Your Recent Support Request\n"
        "Hi Sarah,\n"
        "Thanks for your patience while we looked into the login issue you "
        "reported. It's now fixed, and you should be able to access your "
        "account normally. Let us know if anything still looks off.\n"
        "Best,\nThe Support Team\n\n"
        "Example 2:\n"
        "Subject: Your Refund Has Been Processed\n"
        "Hi James,\n"
        "Your refund of $45.00 has been processed and should appear in your "
        "account within 3-5 business days. We're sorry the item didn't work "
        "out this time -- we'd love to help you find a better fit whenever "
        "you're ready.\n"
        "Warm regards,\nCustomer Care\n\n"
        "Now write a new email in the same style and tone: inform a client "
        "their order is delayed by one week, apologize, and offer a 10% "
        "discount on their next purchase."
    ),

    "3_role_based": (
        "You are a senior customer experience manager at a premium "
        "e-commerce brand, known for turning service hiccups into moments "
        "that build customer loyalty rather than lose it. A client's order "
        "is delayed by one week. Write the email you would personally send "
        "them: apologize sincerely, take ownership without being overly "
        "formal or robotic, and offer a 10% discount on their next purchase "
        "as a goodwill gesture."
    ),

    "4_step_by_step": (
        "Write an email to a client about a one-week order delay, "
        "following these steps in order:\n"
        "1. Open by acknowledging the delay clearly and directly (no burying "
        "the news).\n"
        "2. Apologize sincerely, in one or two sentences -- no over-explaining.\n"
        "3. State the new expected delivery timeframe.\n"
        "4. Offer a 10% discount on their next purchase as an apology gesture.\n"
        "5. Close with a reassuring, appreciative sign-off.\n"
        "Write the final email only, incorporating all five steps smoothly "
        "(don't label the steps in the output)."
    ),

    "5_format_specific": (
        "Write an email to a client about a one-week order delay, apologizing "
        "and offering a 10% discount on their next purchase. Follow this "
        "exact format:\n"
        "- Subject line (under 8 words)\n"
        "- Greeting\n"
        "- Exactly 3 short paragraphs, each no more than 2 sentences\n"
        "- One bullet point summarizing the discount offer\n"
        "- Professional sign-off\n"
        "- Total length under 130 words"
    ),
}
