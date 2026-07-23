class DecisionEngine:
    @staticmethod
    def evaluate_threat(label: str, confidence: float):
        """تصنيف المخاطر بناءً على مصفوفة القرار (صفحة 182)"""
        
        # تحويل الاسم لحروف صغيرة لتجنب أخطاء المقارنة
        label = label.lower()

        # 1. المخاطر الحرجة (تحتاج تدخل فوري)
        critical_threats = ["weapon", "knife", "fire", "flame", "pistol", "gun"]
        if label in critical_threats and confidence > 0.4:
            return "Critical"

        # 2. مخاطر متوسطة
        high_threats = ["smoke"]
        if label in high_threats:
            return "High"

        # 3. أحداث عادية (للمراقبة فقط)
        if label == "person":
            return "Low"

        return "Informational"